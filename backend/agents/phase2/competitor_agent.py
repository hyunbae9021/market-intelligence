"""
Agent #7: 경쟁사/동종업계 분석 Agent
역할: 주요 경쟁사 및 동종업계 심층 분석
Phase 2 - 분석 & 심층 리서치

품질 기준:
- 분석 대상 15개사 이상
- 정량/정성 균형
- 프레임워크 일관성
- 최신 데이터 기반 (3개월 이내)
"""
from __future__ import annotations

from typing import Any, Dict

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentContext, AgentPhase, QualityCheck, QualityLevel, QualityReport


class CompetitorAgent(BaseAgent):
    AGENT_ID   = "p2_competitor"
    AGENT_NAME = "경쟁사/동종업계 분석 Agent"
    PHASE      = AgentPhase.PHASE2_ANALYSIS

    ROLE = "주요 경쟁사 및 동종업계 심층 분석"
    TASKS = [
        "경쟁사 사업모델/수익구조 분석",
        "제품/서비스 비교",
        "SWOT 분석",
        "경쟁 포지셔닝 맵 작성",
    ]
    OUTPUT_TYPES = [
        "경쟁사 프로파일 심층 리포트",
        "비교 분석 매트릭스",
        "SWOT 분석표",
        "포지셔닝 맵 (MD+XLSX)",
    ]
    QUALITY_CRITERIA = [
        "분석 대상 15개사 이상",
        "정량/정성 균형",
        "프레임워크 일관성",
        "최신 데이터 기반 (3개월 이내)",
    ]
    DATA_SOURCES = ["Phase 1 기업 정보", "기업 IR/연간보고서", "업계 리서치 리포트"]
    API_TOOLS   = ["Phase 1 Agent 결과물", "LinkedIn API", "Owler API"]

    async def collect_data(self, context: AgentContext) -> Dict[str, Any]:
        prev = context.previous_results
        data = {}

        if "p1_company" in prev:
            company_output = prev["p1_company"]
            data["company_raw"] = company_output.raw_data
            data["company_analysis"] = company_output.analysis

        if "p1_news" in prev:
            data["news_analysis"] = prev["p1_news"].analysis

        data["target_companies"] = context.scope.target_companies
        data["topic"] = context.scope.topic
        return data

    async def analyze(self, context: AgentContext, raw_data: Dict[str, Any]) -> str:
        company_analysis = raw_data.get("company_analysis", "")
        exchanges = raw_data.get("company_raw", {}).get("exchanges", [])[:15]

        exchange_text = "\n".join([
            f"- {ex.get('name', '')} ({ex.get('country', '')}): "
            f"거래량 {ex.get('volume_24h_btc', 0):.0f} BTC/24h, "
            f"신뢰점수 {ex.get('trust_score', 0)}/10, "
            f"설립 {ex.get('year_established', 'N/A')}"
            for ex in exchanges if "error" not in ex
        ])

        system = """당신은 Market Intelligence 경쟁 분석 전문가입니다.
핵심 원칙:
- 기업 프로파일에는 반드시 정량 지표(시가총액/밸류에이션, 매출, 사용자 수, 점유율)를 포함하세요
- 비교 분석은 반드시 표 형식으로 작성하세요
- 각 기업의 사업모델과 수익 구조를 Value Chain 관점에서 분석하세요
- 투자/IPO/M&A 정보 등 최근 동향을 수치와 함께 제시하세요
- 데이터 출처를 명시하세요
반드시 한국어로 작성하고, Markdown 형식을 사용하세요."""

        target_companies = context.scope.target_companies or ["Coinbase", "Binance", "OKX", "Bybit", "Upbit"]
        companies_str = ", ".join(target_companies[:10])

        prompt = f"""
리서치 주제: {context.scope.topic}
분석 대상 기업: {companies_str}
데이터 수집 기간: 최근 {context.scope.date_range_days}일

## 경쟁사 실시간 데이터
{exchange_text if exchange_text else '데이터 없음'}

## Phase 1 기업 분석 요약
{(company_analysis or '')[:2500]}

위 데이터를 바탕으로 다음 형식의 심층 경쟁 분석 리포트를 작성하세요:

---

## 핵심 요약
> (경쟁 구도의 핵심 특징과 가장 중요한 발견을 수치와 함께 2-3문장으로)

## 1. 경쟁 구도 개요

| 구분 | 기업 | 특징 | 시장 점유율(추정) |
|------|------|------|----------------|
| 시장 리더 | | | |
| 챌린저 | | | |
| 니처 | | | |

**"** (경쟁 구도 핵심 인사이트) **"**

## 2. 주요 기업 프로파일 (상위 5~8개사)

각 기업 형식:
### [기업명] — [창업연도] | [국가] | [상장 여부]
| 항목 | 내용 |
|------|------|
| 밸류에이션/시가총액 | $XB (기준일) |
| 주요 사업 | |
| 수익 구조 | |
| 24시간 거래량 | |
| 사용자 수 | |
| 최근 주요 이슈 | |

**강점**: / **약점**: / **경쟁 강도**: 상/중/하

## 3. 비교 분석 매트릭스

| 기업 | 밸류에이션 | 거래량(24h) | 수수료율 | 글로벌 진출 | 규제 준수 | 기술 혁신 | 종합 |
|------|---------|-----------|--------|-----------|---------|---------|-----|

## 4. Value Chain 관점 경쟁 분석

| Value Chain 영역 | 주요 플레이어 | 수익 모델 | 시장 집중도 |
|----------------|-----------|---------|-----------|
| 발행 (Issuance) | | | |
| 유통 (Distribution) | | | |
| 인프라 (Infrastructure) | | | |
| Use Case (응용) | | | |

## 5. SWOT 분석 (당사 관점)

| 구분 | 내용 | 관련 경쟁사 |
|------|------|-----------|
| **Strengths** | | |
| **Weaknesses** | | |
| **Opportunities** | | |
| **Threats** | | |

## 6. 경쟁사 최근 전략 동향

| 기업 | 주요 동향 | 시기 | 전략적 의미 | 당사 영향 |
|------|---------|------|-----------|---------|

## 7. 경쟁 포지셔닝 분석
- **글로벌화 ↔ 로컬** × **혁신성 ↔ 안정성** 2×2 매트릭스 기준
- 각 주요 기업 포지션 및 이동 방향

## 8. 전략적 시사점 및 권고

| 기간 | 권고 행동 | 근거 | 우선순위 |
|------|---------|------|--------|
| 단기 (3개월) | | | |
| 중기 (6~12개월) | | | |
| 장기 (2년+) | | | |
"""
        return await self._claude(system, prompt, max_tokens=4096)

    async def validate(self, output, context: AgentContext) -> QualityReport:
        checks = []
        analysis = output.analysis or ""

        has_swot = "SWOT" in analysis or ("강점" in analysis and "약점" in analysis)
        checks.append(QualityCheck(
            criterion="SWOT 분석 포함",
            target="Strengths/Weaknesses/Opportunities/Threats",
            actual="포함" if has_swot else "미포함",
            level=QualityLevel.PASS if has_swot else QualityLevel.FAIL,
        ))

        has_matrix = "매트릭스" in analysis or "|" in analysis
        checks.append(QualityCheck(
            criterion="비교 분석 매트릭스 포함",
            target="표 형식 비교 포함",
            actual="포함" if has_matrix else "미포함",
            level=QualityLevel.PASS if has_matrix else QualityLevel.WARNING,
        ))

        has_positioning = "포지셔닝" in analysis
        checks.append(QualityCheck(
            criterion="포지셔닝 맵 포함",
            target="포함",
            actual="포함" if has_positioning else "미포함",
            level=QualityLevel.PASS if has_positioning else QualityLevel.WARNING,
        ))

        pass_count = sum(1 for c in checks if c.level == QualityLevel.PASS)
        pass_rate = pass_count / len(checks)
        return QualityReport(
            overall=QualityLevel.PASS if pass_rate >= 0.67 else QualityLevel.WARNING,
            checks=checks,
            pass_rate=pass_rate,
            summary=f"{len(checks)}개 항목 중 {pass_count}개 통과",
        )
