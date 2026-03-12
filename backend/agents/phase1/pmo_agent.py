"""
Agent #1: PMO Agent
역할: MI 프로젝트 총괄 관리
Phase 1 - 데이터 수집
"""
from __future__ import annotations

from typing import Any, Dict

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentContext, AgentPhase


class PMOAgent(BaseAgent):
    AGENT_ID   = "p1_pmo"
    AGENT_NAME = "PMO Agent"
    PHASE      = AgentPhase.PHASE1_COLLECTION

    ROLE = "MI 프로젝트 총괄 관리"
    TASKS = [
        "리서치 주제/범위/일정 설정",
        "에이전트별 워크플로 설계 및 업무 분배",
        "수집 데이터 품질 모니터링",
        "각 Agent 결과물 통합 관리",
    ]
    OUTPUT_TYPES = [
        "프로젝트 킥오프 문서",
        "리서치 브리프",
        "에이전트 워크플로 맵",
        "진행 현황 대시보드",
    ]
    QUALITY_CRITERIA = [
        "리서치 범위의 명확성",
        "Agent별 업무 배분 적정성",
        "누락 분석 항목 0",
    ]
    DATA_SOURCES = ["이전 MI 리포트", "회사 전략 문서", "경영진 OKR"]
    API_TOOLS   = ["Notion API", "Slack API", "Jira API"]

    async def collect_data(self, context: AgentContext) -> Dict[str, Any]:
        """리서치 범위와 워크플로 정의"""
        scope = context.scope
        return {
            "topic": scope.topic,
            "industries": scope.industries,
            "target_companies": scope.target_companies,
            "regions": scope.regions,
            "date_range_days": scope.date_range_days,
            "custom_instructions": scope.custom_instructions,
            "agent_workflow": {
                "phase1": ["p1_news", "p1_industry", "p1_regulatory", "p1_company"],
                "phase2": ["p2_market", "p2_competitor", "p2_tech", "p2_bizmodel"],
                "phase3": ["p3_insight", "p3_strategy", "p3_qa"],
                "phase4": ["p4_report", "p4_dashboard"],
            },
            "source": "PMO 설정",
        }

    async def analyze(self, context: AgentContext, raw_data: Dict[str, Any]) -> str:
        system = """당신은 Market Intelligence 프로젝트 매니저입니다.
리서치 범위를 분석하고 명확한 프로젝트 브리프와 워크플로를 작성하세요.
반드시 한국어로 작성하고, Markdown 형식을 사용하세요."""

        prompt = f"""
다음 리서치 요청을 분석하여 MI 프로젝트 브리프를 작성하세요:

**리서치 주제**: {raw_data['topic']}
**분석 대상 산업**: {', '.join(raw_data['industries']) if raw_data['industries'] else '전체'}
**분석 대상 기업**: {', '.join(raw_data['target_companies']) if raw_data['target_companies'] else '미지정'}
**대상 지역**: {', '.join(raw_data['regions'])}
**데이터 수집 기간**: 최근 {raw_data['date_range_days']}일
**추가 지시사항**: {raw_data.get('custom_instructions') or '없음'}

다음 구조로 프로젝트 브리프를 작성하세요:

## 1. 리서치 개요
- 목적 및 배경
- 핵심 질문 (Key Questions) 5개

## 2. 분석 범위
- 포함 항목
- 제외 항목
- 중점 분석 영역

## 3. 에이전트 워크플로
- Phase 1 (데이터 수집): 어떤 데이터를 수집할지
- Phase 2 (분석): 어떤 분석을 할지
- Phase 3 (종합): 어떤 인사이트를 도출할지
- Phase 4 (산출물): 최종 결과물 형태

## 4. 품질 기준
- 데이터 최신성 기준
- 출처 다양성 기준
- 분석 깊이 기준

## 5. 리스크 및 주의사항
"""
        return await self._claude(system, prompt, max_tokens=4000)
