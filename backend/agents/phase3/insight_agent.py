"""
Agent #10: 인사이트 종합 Agent
역할: 전체 분석 결과 종합 및 핵심 인사이트 도출
Phase 3 - 종합 & 인사이트

품질 기준:
- 인사이트의 논리적 일관성
- Phase 1-2 결과물 100% 반영
- 핵심 발견 5개 이상
- 근거 데이터 명시
"""
from __future__ import annotations

from typing import Any, Dict

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentContext, AgentPhase, QualityCheck, QualityLevel, QualityReport


class InsightAgent(BaseAgent):
    AGENT_ID   = "p3_insight"
    AGENT_NAME = "인사이트 종합 Agent"
    PHASE      = AgentPhase.PHASE3_SYNTHESIS

    ROLE = "전체 분석 결과 종합 및 핵심 인사이트 도출"
    TASKS = [
        "Phase 1-2 전체 결과물 크로스 분석",
        "산업간 교차 인사이트 도출",
        "시장 기회/위험 요인 종합 평가",
        "데이터 간 상충점 식별 및 해소",
    ]
    OUTPUT_TYPES = [
        "종합 인사이트 리포트",
        "기회/위험 매트릭스",
        "핵심 발견사항 요약",
        "산업간 시너지 분석 (MD+XLSX)",
    ]
    QUALITY_CRITERIA = [
        "인사이트의 논리적 일관성",
        "Phase 1-2 결과물 100% 반영",
        "핵심 발견 5개 이상",
        "근거 데이터 명시",
    ]
    DATA_SOURCES = ["Phase 1-2 전체 Agent 결과물"]
    API_TOOLS   = ["Phase 1-2 Agent 결과물", "Claude API (분석 보조)"]

    async def collect_data(self, context: AgentContext) -> Dict[str, Any]:
        prev = context.previous_results

        synthesis = {
            "topic": context.scope.topic,
            "phase1_summaries": {},
            "phase2_summaries": {},
        }

        # Phase 1 결과 수집
        phase1_agents = ["p1_pmo", "p1_news", "p1_industry", "p1_regulatory", "p1_company"]
        for agent_id in phase1_agents:
            if agent_id in prev:
                synthesis["phase1_summaries"][agent_id] = {
                    "name": prev[agent_id].agent_name,
                    "summary": prev[agent_id].summary,
                    "analysis": (prev[agent_id].analysis or "")[:3000],
                    "data_points": prev[agent_id].data_points_collected,
                }

        # Phase 2 결과 수집
        phase2_agents = ["p2_market", "p2_competitor", "p2_tech", "p2_bizmodel"]
        for agent_id in phase2_agents:
            if agent_id in prev:
                synthesis["phase2_summaries"][agent_id] = {
                    "name": prev[agent_id].agent_name,
                    "summary": prev[agent_id].summary,
                    "analysis": (prev[agent_id].analysis or "")[:3000],
                }

        synthesis["agents_completed"] = len(synthesis["phase1_summaries"]) + len(synthesis["phase2_summaries"])
        return synthesis

    async def analyze(self, context: AgentContext, raw_data: Dict[str, Any]) -> str:
        p1_text = "\n\n---\n\n".join([
            f"### {v['name']} (데이터포인트: {v.get('data_points', 0)}개)\n**요약**: {v['summary']}\n\n{v['analysis']}"
            for v in raw_data.get("phase1_summaries", {}).values()
        ])

        p2_text = "\n\n---\n\n".join([
            f"### {v['name']}\n**요약**: {v['summary']}\n\n{v['analysis']}"
            for v in raw_data.get("phase2_summaries", {}).values()
        ])

        total_agents = raw_data.get("agents_completed", 0)

        system = """당신은 시장 조사 리포트를 작성하는 최고 전략 분석가입니다.
핵심 원칙:
- 인사이트는 구체적 수치(시장 규모, 성장률, 점유율 등)와 반드시 함께 제시하세요
- 각 인사이트는 "~이다" 형태의 단호한 주장으로 시작하고, 그 근거를 수치로 뒷받침하세요
- 기회/위험은 반드시 정량적으로 서술하세요 (예: "X시장 $YB 규모, 연 Z% 성장")
- 출처와 에이전트 참조를 명시하세요
- 불확실한 추측은 "추정" "가능성" 등 명확히 구분 표시하세요
반드시 한국어로 작성하고, Markdown 형식을 사용하세요."""

        prompt = f"""
리서치 주제: {context.scope.topic}
분석 기간: 최근 {context.scope.date_range_days}일
분석에 참여한 에이전트: {total_agents}개

## Phase 1 (데이터 수집) 결과
{p1_text[:8000] if p1_text else '데이터 없음'}

## Phase 2 (심층 분석) 결과
{p2_text[:8000] if p2_text else '데이터 없음'}

위 모든 분석 결과를 종합하여 다음 형식의 핵심 인사이트 리포트를 작성하세요:

---

## Executive Summary
> (전체 분석의 가장 중요한 결론 3가지를 수치와 함께 bullet로 요약)

## 1. 핵심 인사이트 (최소 7개)

각 인사이트 형식:
### 인사이트 #N: [인사이트 제목 — 핵심 주장 1문장]
> **"** (이 인사이트의 핵심 메시지를 인용구 형태로) **"**

- **근거 수치**: (구체적 수치, 데이터 출처)
- **관련 에이전트**: (어느 에이전트의 데이터 기반인지)
- **시장 의미**: (이것이 시장에서 의미하는 바)
- **사업적 시사점**: (우리 회사는 무엇을 해야 하나)
- **확신도**: 높음/중간/낮음 (근거: )

## 2. 기회/위험 종합 매트릭스

| 구분 | 항목 | 시장 규모(추정) | 발생 가능성 | 영향도 | 대응 우선순위 |
|------|------|--------------|-----------|--------|-------------|
| 기회 | | $XB | 상/중/하 | 상/중/하 | 1~5 |
| 기회 | | | | | |
| 위험 | | | | | |
| 위험 | | | | | |

## 3. 산업/기술 교차 인사이트

| 교차 영역 | 핵심 발견 | 정량 근거 | 사업 기회 |
|---------|---------|---------|---------|
| (예) 스테이블코인 × 결제 | | | |
| (예) AI × 금융 | | | |
| (예) 규제 × 시장 타이밍 | | | |

## 4. 데이터 상충점 및 불확실성

| 상충 항목 | 에이전트 A 주장 | 에이전트 B 주장 | 해소 방안 | 현재 확신도 |
|---------|-------------|-------------|---------|---------|

## 5. 확신 수준별 결론 분류

### 높은 확신 (근거 충분)
- (수치와 출처 포함)

### 중간 확신 (추가 검증 권고)
- (어떤 추가 데이터가 필요한지)

### 불확실 (추정 영역)
- (추정의 전제 조건 명시)

## 6. 종합 시장 평가 스코어카드

| 평가 항목 | 점수 (/10) | 근거 | 트렌드 |
|---------|---------|------|------|
| 투자 매력도 | | | ↑/→/↓ |
| 경쟁 강도 | | | |
| 성장성 | | | |
| 규제 리스크 | | | |
| 기술 성숙도 | | | |
| **종합** | | | |
"""
        return await self._claude(system, prompt, max_tokens=16000)

    async def validate(self, output, context: AgentContext) -> QualityReport:
        checks = []
        analysis = output.analysis or ""

        # 핵심 발견 5개 이상
        insight_count = analysis.count("### 인사이트") + analysis.count("인사이트 #")
        checks.append(QualityCheck(
            criterion="핵심 인사이트 수 (5개 이상)",
            target="5개 이상",
            actual=f"{insight_count}개",
            level=QualityLevel.PASS if insight_count >= 5 else QualityLevel.WARNING,
        ))

        # 기회/위험 매트릭스
        has_matrix = "기회" in analysis and "위험" in analysis and "매트릭스" in analysis
        checks.append(QualityCheck(
            criterion="기회/위험 매트릭스 포함",
            target="포함",
            actual="포함" if has_matrix else "미포함",
            level=QualityLevel.PASS if has_matrix else QualityLevel.WARNING,
        ))

        # Phase 1-2 반영
        agents_count = raw_data_count = len(output.raw_data.get("phase1_summaries", {})) + len(output.raw_data.get("phase2_summaries", {}))
        checks.append(QualityCheck(
            criterion="Phase 1-2 결과물 반영",
            target="6개 이상 에이전트 결과 반영",
            actual=f"{agents_count}개 에이전트",
            level=QualityLevel.PASS if agents_count >= 6 else QualityLevel.WARNING,
        ))

        pass_count = sum(1 for c in checks if c.level == QualityLevel.PASS)
        pass_rate = pass_count / len(checks)
        return QualityReport(
            overall=QualityLevel.PASS if pass_rate >= 0.67 else QualityLevel.WARNING,
            checks=checks,
            pass_rate=pass_rate,
            summary=f"{len(checks)}개 항목 중 {pass_count}개 통과",
        )
