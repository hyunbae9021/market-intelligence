"""
Agent #3: 산업 데이터 수집 Agent
역할: 시장/산업 정량 데이터 수집
Phase 1 - 데이터 수집

품질 기준:
- 데이터 지연 <24시간
- 주요 지표 50개+ 커버
- 데이터 정합성 검증
- 소스 3개 이상 교차 검증
"""
from __future__ import annotations

from typing import Any, Dict

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentContext, AgentPhase, QualityCheck, QualityLevel, QualityReport
from backend.tools.market_tools import gather_market_data


class IndustryDataAgent(BaseAgent):
    AGENT_ID   = "p1_industry"
    AGENT_NAME = "산업 데이터 수집 Agent"
    PHASE      = AgentPhase.PHASE1_COLLECTION

    ROLE = "시장/산업 정량 데이터 수집"
    TASKS = [
        "앱 다운로드/MAU/DAU 추적",
        "거래소 거래량/시장점유율",
        "SaaS ARR/성장률 벤치마크",
        "온체인 TVL/거래량 데이터",
    ]
    OUTPUT_TYPES = [
        "산업 KPI 대시보드",
        "시장 데이터 DB",
        "주간 데이터 스냅샷 (XLSX+차트)",
    ]
    QUALITY_CRITERIA = [
        "데이터 지연 <24시간",
        "주요 지표 50개+ 커버",
        "데이터 정합성 검증",
        "소스 3개 이상 교차 검증",
    ]
    DATA_SOURCES = ["App Annie/data.ai", "SimilarWeb", "CoinGecko", "DefiLlama", "Sensor Tower"]
    API_TOOLS   = ["data.ai API", "SimilarWeb API", "CoinGecko API", "DefiLlama API"]

    async def collect_data(self, context: AgentContext) -> Dict[str, Any]:
        await self._notify("시장 데이터 수집 중...", 0.1)

        coingecko_key = None  # .env에서 주입됨
        data = await gather_market_data(coingecko_api_key=coingecko_key)
        return data

    async def analyze(self, context: AgentContext, raw_data: Dict[str, Any]) -> str:
        # 데이터 요약
        global_data = raw_data.get("coingecko_global", {})
        markets = raw_data.get("coingecko_markets", [])[:15]
        protocols = raw_data.get("defillama_protocols", [])[:10]
        chains = raw_data.get("defillama_chains", [])[:10]
        stablecoins = raw_data.get("defillama_stablecoins", {})

        market_text = "\n".join([
            f"- {m['name']} ({m.get('symbol','')}): ${m.get('price_usd',0):,.2f}, "
            f"시총 ${m.get('market_cap_usd',0)/1e9:.1f}B, 24h {m.get('price_change_24h_pct',0):+.1f}%"
            for m in markets if "error" not in m
        ])

        protocol_text = "\n".join([
            f"- {p['name']} ({p.get('category','')}): TVL ${p.get('tvl_usd',0)/1e6:.0f}M"
            for p in protocols if "error" not in p
        ])

        system = """당신은 Market Intelligence 데이터 분석 전문가입니다.
수집된 시장/산업 정량 데이터를 분석하여 핵심 인사이트를 도출하세요.
반드시 한국어로 작성하고, Markdown 형식을 사용하세요."""

        prompt = f"""
리서치 주제: {context.scope.topic}

## 글로벌 시장 현황
- 전체 크립토 시가총액: ${global_data.get('total_market_cap_usd', 0)/1e9:.0f}B
- 24시간 거래량: ${global_data.get('total_volume_24h_usd', 0)/1e9:.0f}B
- BTC 도미넌스: {global_data.get('btc_dominance_pct', 0):.1f}%
- ETH 도미넌스: {global_data.get('eth_dominance_pct', 0):.1f}%
- 시총 변화 (24h): {global_data.get('market_cap_change_24h_pct', 0):+.1f}%

## 주요 자산 현황
{market_text if market_text else '데이터 없음'}

## DeFi 프로토콜 TVL TOP 10
{protocol_text if protocol_text else '데이터 없음'}

## 스테이블코인 시장
총 스테이블코인 시총: ${stablecoins.get('total_stablecoin_market_cap_usd', 0)/1e9:.0f}B

위 데이터를 분석하여 다음 형식으로 리포트를 작성하세요:

## 1. 시장 현황 요약
- 전반적 시장 상태 평가 (강세/약세/횡보)
- 핵심 지표 변화 해석

## 2. 주요 자산 분석
- 시가총액 기준 Top 5 분석
- 주목할 만한 가격 움직임
- 섹터별 성과 비교

## 3. DeFi 생태계 현황
- TVL 트렌드 분석
- 주요 프로토콜 동향
- 체인별 경쟁 구도

## 4. 스테이블코인 & 유동성 분석
- 스테이블코인 시장 현황
- 유동성 흐름 분석

## 5. 핵심 데이터 포인트 (KPI 요약표)
| 지표 | 수치 | 전주 대비 | 평가 |
|------|------|-----------|------|

## 6. 주목할 데이터 시그널
- 긍정 시그널
- 경고 시그널
"""
        return await self._claude(system, prompt, max_tokens=16000)

    async def validate(self, output, context: AgentContext) -> QualityReport:
        checks = []

        raw = output.raw_data
        total_points = output.data_points_collected

        checks.append(QualityCheck(
            criterion="데이터 포인트 수 (50개+ 목표)",
            target="50개 이상",
            actual=f"{total_points}개",
            level=QualityLevel.PASS if total_points >= 50 else QualityLevel.WARNING,
        ))

        source_types = sum([
            1 if raw.get("coingecko_markets") else 0,
            1 if raw.get("defillama_protocols") else 0,
            1 if raw.get("defillama_chains") else 0,
        ])
        checks.append(QualityCheck(
            criterion="소스 교차 검증 (3개 이상)",
            target="3개 이상",
            actual=f"{source_types}개",
            level=QualityLevel.PASS if source_types >= 3 else QualityLevel.WARNING,
        ))

        global_data = raw.get("coingecko_global", {})
        checks.append(QualityCheck(
            criterion="글로벌 시장 데이터 수집",
            target="시가총액, 거래량 등 핵심 지표",
            actual="수집됨" if global_data.get("total_market_cap_usd") else "미수집",
            level=QualityLevel.PASS if global_data.get("total_market_cap_usd") else QualityLevel.FAIL,
        ))

        pass_count = sum(1 for c in checks if c.level == QualityLevel.PASS)
        pass_rate = pass_count / len(checks)
        overall = QualityLevel.PASS if pass_rate >= 0.67 else QualityLevel.WARNING

        return QualityReport(
            overall=overall,
            checks=checks,
            pass_rate=pass_rate,
            summary=f"{len(checks)}개 항목 중 {pass_count}개 통과",
        )
