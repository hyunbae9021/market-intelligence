"""
Agent #11: 전략 시사점 Agent
역할: 당사 관점의 전략적 시사점 도출
Phase 3 - 종합 & 인사이트
"""
from __future__ import annotations

from typing import Any, Dict

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentContext, AgentPhase, QualityCheck, QualityLevel, QualityReport


class StrategyAgent(BaseAgent):
    AGENT_ID   = "p3_strategy"
    AGENT_NAME = "전략 시사점 Agent"
    PHASE      = AgentPhase.PHASE3_SYNTHESIS

    ROLE = "당사 관점의 전략적 시사점 도출"
    TASKS = [
        "당사 사업 영향도 분석",
        "신규 사업/투자 기회 평가",
        "리스크 요인 및 대응 방안 도출",
        "실행 우선순위 및 로드맵 초안 작성",
    ]
    OUTPUT_TYPES = [
        "전략 시사점 리포트",
        "사업 기회 평가표",
        "리스크 매트릭스",
        "실행 로드맵 초안 (MD+XLSX)",
    ]
    QUALITY_CRITERIA = [
        "당사 전략과의 정합성",
        "실행가능성 평가 포함",
        "정량적 기대효과 추정",
        "리스크 대응 방안 구체성",
    ]
    DATA_SOURCES = ["인사이트 종합 결과", "당사 전략/사업계획", "경영진 OKR", "내부 역량 분석 자료"]
    API_TOOLS   = ["Phase 1-3 Agent 결과물", "내부 전략 DB"]

    async def collect_data(self, context: AgentContext) -> Dict[str, Any]:
        prev = context.previous_results
        data = {"topic": context.scope.topic}

        # 핵심 분석 결과 수집
        for agent_id in ["p3_insight", "p2_market", "p2_competitor", "p2_bizmodel", "p1_regulatory"]:
            if agent_id in prev:
                data[agent_id] = {
                    "summary": prev[agent_id].summary,
                    "analysis": (prev[agent_id].analysis or "")[:600],
                }

        return data

    async def analyze(self, context: AgentContext, raw_data: Dict[str, Any]) -> str:
        insight_data = raw_data.get("p3_insight", {})
        market_data = raw_data.get("p2_market", {})
        competitor_data = raw_data.get("p2_competitor", {})
        regulatory_data = raw_data.get("p1_regulatory", {})
        bizmodel_data = raw_data.get("p2_bizmodel", {})

        system = """당신은 C-레벨 전략 컨설턴트입니다. McKinsey 수준의 전략 리포트를 작성하세요.
핵심 원칙:
- 모든 사업 기회에는 시장 규모($B), 성장률(%), 수익성(마진%) 수치를 포함하세요
- 기대효과는 반드시 정량적으로 추정하세요 (매출 X억, 시장점유율 X%)
- 투자/파트너십 대상 기업은 실제 기업명과 밸류에이션 수치를 포함하세요
- 각 권고의 근거가 되는 시장/경쟁 데이터를 명시하세요
- Value Chain 관점에서 사업 기회를 분류하세요 (발행/유통/인프라/Use Case)
반드시 한국어로 작성하고, Markdown 형식을 사용하세요."""

        prompt = f"""
리서치 주제: {context.scope.topic}
분석 기간: 최근 {context.scope.date_range_days}일

## 핵심 인사이트 요약
{insight_data.get('summary', '데이터 없음')}
{insight_data.get('analysis', '')[:800]}

## 시장 분석 요약
{market_data.get('summary', '')}
{market_data.get('analysis', '')[:500]}

## 경쟁사 분석 요약
{competitor_data.get('summary', '')}
{competitor_data.get('analysis', '')[:500]}

## 규제 동향 요약
{regulatory_data.get('summary', '')}

## 사업 기회 분석 요약
{bizmodel_data.get('summary', '')}
{bizmodel_data.get('analysis', '')[:400]}

위 분석을 바탕으로 다음 형식의 전략 시사점 리포트를 작성하세요:

---

## 핵심 전략 결론
> **"** (가장 중요한 전략적 결론을 수치와 함께 1-2문장으로) **"**

## 1. Value Chain 관점 사업 기회 분석

| Value Chain | 기회 영역 | 시장 규모 | 성장률 | 당사 진입 가능성 | 우선순위 |
|------------|---------|---------|------|--------------|--------|
| 발행 | | $XB | X%YoY | 상/중/하 | |
| 유통 | | | | | |
| 인프라 | | | | | |
| Use Case | | | | | |

## 2. 사업 기회 우선순위 매트릭스

| 기회 | 시장 규모 | CAGR | 경쟁 강도 | 당사 역량 적합도 | 예상 수익성 | 우선순위 |
|------|---------|------|---------|--------------|---------|--------|
| 1순위 | $XB | X% | 상/중/하 | 상/중/하 | X% 마진 | **최우선** |
| 2순위 | | | | | | |
| 3순위 | | | | | | |

## 3. 리스크 매트릭스 및 대응 방안

| 리스크 | 유형 | 발생확률 | 영향도 | 대응 방안 | 기한 | 담당 |
|--------|------|---------|--------|---------|-----|-----|
| | 규제/시장/기술/운영 | 상/중/하 | 상/중/하 | | | |

## 4. 전략적 권고 — 단계별 액션 플랜

### Phase 1: 즉시 실행 (0~3개월)
| 액션 | 목적 | 정량적 기대효과 | 필요 투자 | 담당 |
|------|------|--------------|---------|-----|

### Phase 2: 단기 과제 (3~6개월)
| 액션 | 목적 | 정량적 기대효과 | 필요 투자 | 담당 |
|------|------|--------------|---------|-----|

### Phase 3: 중기 전략 (6~12개월)
| 액션 | 목적 | 정량적 기대효과 | 필요 투자 | KPI |
|------|------|--------------|---------|-----|

### Phase 4: 장기 비전 (1~3년)
- **목표 포지셔닝**: (시장 내 위치, 목표 점유율 %)
- **핵심 역량 개발**: (무엇을, 어떻게)
- **목표 사업 규모**: $XB 또는 X억원

## 5. 투자/파트너십 권고

| 구분 | 대상 기업/영역 | 밸류에이션(추정) | 전략적 이유 | 우선순위 |
|------|------------|--------------|---------|--------|
| 직접 투자 검토 | | $XB | | |
| 전략적 파트너십 | | | | |
| M&A 검토 | | | | |

## 6. 실행 로드맵 — 분기별 마일스톤

| 분기 | 핵심 과제 | KPI 목표 | 완료 기준 |
|------|---------|---------|---------|
| '25 Q2 | | | |
| '25 Q3 | | | |
| '25 Q4 | | | |
| '26 H1 | | | |

## 7. 경영진 보고 핵심 메시지

> **메시지 1**: (수치 포함 핵심 기회)
> **메시지 2**: (수치 포함 핵심 리스크)
> **메시지 3**: (즉각 결정이 필요한 사항)
"""
        return await self._claude(system, prompt, max_tokens=4096)

    async def validate(self, output, context: AgentContext) -> QualityReport:
        checks = []
        analysis = output.analysis or ""

        has_roadmap = "로드맵" in analysis and ("0~3개월" in analysis or "즉시" in analysis)
        checks.append(QualityCheck(
            criterion="실행 로드맵 포함",
            target="단계별 실행 계획",
            actual="포함" if has_roadmap else "미포함",
            level=QualityLevel.PASS if has_roadmap else QualityLevel.FAIL,
        ))

        has_risk = "리스크" in analysis and "대응" in analysis
        checks.append(QualityCheck(
            criterion="리스크 매트릭스 및 대응 방안",
            target="포함",
            actual="포함" if has_risk else "미포함",
            level=QualityLevel.PASS if has_risk else QualityLevel.WARNING,
        ))

        has_quantitative = "억" in analysis or "%" in analysis or "목표 매출" in analysis
        checks.append(QualityCheck(
            criterion="정량적 기대효과 추정",
            target="수치 기반 효과 포함",
            actual="포함" if has_quantitative else "미포함",
            level=QualityLevel.PASS if has_quantitative else QualityLevel.WARNING,
        ))

        pass_count = sum(1 for c in checks if c.level == QualityLevel.PASS)
        pass_rate = pass_count / len(checks)
        return QualityReport(
            overall=QualityLevel.PASS if pass_rate >= 0.67 else QualityLevel.WARNING,
            checks=checks,
            pass_rate=pass_rate,
            summary=f"{len(checks)}개 항목 중 {pass_count}개 통과",
        )
