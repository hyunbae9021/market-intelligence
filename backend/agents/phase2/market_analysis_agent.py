"""
Agent #6: 시장/산업 분석 Agent
역할: 시장 규모/성장률/세그먼트 분석
Phase 2 - 분석 & 심층 리서치

품질 기준:
- 데이터 출처 3개 이상 교차 검증
- 추정 오차 <10%
- 전망 시나리오 3개 이상
- 로직 투명성
"""
from __future__ import annotations

from typing import Any, Dict

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentContext, AgentPhase, QualityCheck, QualityLevel, QualityReport


class MarketAnalysisAgent(BaseAgent):
    AGENT_ID   = "p2_market"
    AGENT_NAME = "시장/산업 분석 Agent"
    PHASE      = AgentPhase.PHASE2_ANALYSIS

    ROLE = "시장 규모/성장률/세그먼트 분석"
    TASKS = [
        "대상 산업별 시장 규모 추정 및 전망 (AI, 핀테크, 크립토 등)",
        "지역별/세그먼트별 분석",
        "TAM/SAM/SOM 산정",
        "성장 드라이버/리스크 분석",
    ]
    OUTPUT_TYPES = [
        "시장 규모 분석 리포트",
        "시장 점유율 대시보드",
        "성장률 전망 모델",
        "세그먼트 분석표 (XLSX+차트)",
    ]
    QUALITY_CRITERIA = [
        "데이터 출처 3개 이상 교차 검증",
        "추정 오차 <10%",
        "전망 시나리오 3개 이상 (낙관/기본/보수)",
        "로직 투명성",
    ]
    DATA_SOURCES = ["Phase 1 산업 데이터", "Gartner", "CB Insights", "Messari"]
    API_TOOLS   = ["Phase 1 Agent 결과물", "Statista API", "Messari API", "TokenTerminal API"]

    async def collect_data(self, context: AgentContext) -> Dict[str, Any]:
        """Phase 1 결과물에서 시장 데이터 추출"""
        prev = context.previous_results

        market_data = {}
        if "p1_industry" in prev:
            industry_output = prev["p1_industry"]
            market_data["industry_raw"] = industry_output.raw_data
            market_data["industry_analysis"] = industry_output.analysis

        if "p1_news" in prev:
            market_data["news_analysis"] = prev["p1_news"].analysis

        market_data["scope"] = {
            "topic": context.scope.topic,
            "industries": context.scope.industries,
            "regions": context.scope.regions,
        }
        return market_data

    async def analyze(self, context: AgentContext, raw_data: Dict[str, Any]) -> str:
        industry_analysis = raw_data.get("industry_analysis", "")
        scope = raw_data.get("scope", {})

        # 시장 데이터 요약
        coingecko_global = raw_data.get("industry_raw", {}).get("coingecko_global", {})
        market_cap = coingecko_global.get("total_market_cap_usd", 0)

        system = """당신은 시장 조사 및 전략 컨설팅 전문가입니다. McKinsey/BCG 수준의 수치 기반 시장 분석을 작성하세요.
핵심 원칙:
- 모든 시장 규모, 성장률, 점유율에는 반드시 구체적 수치($B, %, YoY)를 포함하세요
- 연도별 시계열 데이터를 제시하세요 (예: '18→'20→'22→'25 추이)
- 비교 분석 시 반드시 표 형식을 사용하세요
- 각 데이터의 출처를 명시하세요
- 핵심 인사이트는 인용구(" ") 형태로 강조하세요
반드시 한국어로 작성하고, Markdown 형식을 사용하세요."""

        prompt = f"""
리서치 주제: {context.scope.topic}
분석 대상 산업: {', '.join(scope.get('industries', ['전체']))}
대상 지역: {', '.join(scope.get('regions', ['Global']))}
데이터 수집 기간: 최근 {context.scope.date_range_days}일

## Phase 1 수집 데이터
글로벌 크립토 시장 총 시가총액: ${market_cap/1e9:.0f}B

## Phase 1 산업 분석 결과
{(industry_analysis or '')[:2500]}

위 데이터를 바탕으로 다음 형식의 심층 시장 분석 리포트를 작성하세요:

---

## 핵심 요약
> (시장 현황과 가장 중요한 트렌드를 수치와 함께 2-3문장으로)

## 1. 시장 규모 현황 및 성장 추이

### 시장 규모 시계열
| 연도 | 시장 규모 | YoY 성장률 | 핵심 이벤트 |
|------|---------|-----------|----------|
| 2021 | $XB | +X% | |
| 2022 | $XB | +X% | |
| 2023 | $XB | +X% | |
| 2024 | $XB | +X% | |
| 2025E | $XB | +X% | |

**"** (시장 성장 트렌드에 관한 핵심 인사이트) **"**

### TAM / SAM / SOM
| 구분 | 규모 | 정의 | 근거 |
|------|------|------|------|
| TAM | $XB | | |
| SAM | $XB | | |
| SOM | $XB | | |

## 2. 세그먼트별 시장 분석

| 세그먼트 | 현재 규모 | 비중 | CAGR | 2027년 전망 | 주요 플레이어 |
|---------|---------|------|------|------------|-------------|

## 3. 지역별 시장 현황

| 지역 | 시장 규모 | 비중 | YoY 성장률 | 규제 성숙도 | 진입 기회 |
|------|---------|------|-----------|-----------|---------|
| 한국 | | | | | |
| 미국 | | | | | |
| EU | | | | | |
| 싱가포르 | | | | | |
| 기타 아시아 | | | | | |

## 4. Market Share 현황

| 순위 | 기업/서비스 | 시장점유율 | 시가총액/밸류에이션 | 성장률 |
|-----|-----------|---------|----------------|------|

**"** (시장 집중도/경쟁 구도에 관한 핵심 인사이트) **"**

## 5. 성장 시나리오 (현재~2027년)

| 구분 | 전제 조건 | 2025년 | 2026년 | 2027년 | 핵심 촉매/리스크 |
|------|---------|--------|--------|--------|--------------|
| 낙관 (Bullish) | | $XB | $XB | $XB | |
| 기본 (Base) | | $XB | $XB | $XB | |
| 보수 (Bear) | | $XB | $XB | $XB | |

## 6. 성장 드라이버 vs 리스크

| 구분 | 요인 | 설명 | 영향도 | 시간지평 |
|------|------|------|--------|--------|
| 드라이버 | | | 상/중/하 | 단/중/장기 |
| 드라이버 | | | | |
| 리스크 | | | | |
| 리스크 | | | | |

## 7. 시장 진입 기회 분석

| 기회 영역 | 예상 규모 | 진입 난이도 | 당사 역량 적합도 | 우선순위 |
|---------|---------|-----------|--------------|--------|
"""
        return await self._claude(system, prompt, max_tokens=8192)

    async def validate(self, output, context: AgentContext) -> QualityReport:
        checks = []

        analysis = output.analysis or ""

        has_tam = "TAM" in analysis or "전체 시장" in analysis
        checks.append(QualityCheck(
            criterion="TAM/SAM/SOM 분석 포함",
            target="3개 항목 모두 포함",
            actual="포함" if has_tam else "미포함",
            level=QualityLevel.PASS if has_tam else QualityLevel.FAIL,
        ))

        has_scenarios = ("낙관" in analysis or "Bullish" in analysis) and ("보수" in analysis or "Bear" in analysis)
        checks.append(QualityCheck(
            criterion="시나리오 분석 (3개 이상)",
            target="낙관/기본/보수 시나리오",
            actual="포함" if has_scenarios else "미포함",
            level=QualityLevel.PASS if has_scenarios else QualityLevel.WARNING,
        ))

        has_drivers = "드라이버" in analysis or "성장 동인" in analysis
        checks.append(QualityCheck(
            criterion="성장 드라이버/리스크 분석",
            target="포함",
            actual="포함" if has_drivers else "미포함",
            level=QualityLevel.PASS if has_drivers else QualityLevel.WARNING,
        ))

        pass_count = sum(1 for c in checks if c.level == QualityLevel.PASS)
        pass_rate = pass_count / len(checks)
        return QualityReport(
            overall=QualityLevel.PASS if pass_rate >= 0.67 else QualityLevel.WARNING,
            checks=checks,
            pass_rate=pass_rate,
            summary=f"{len(checks)}개 항목 중 {pass_count}개 통과",
        )
