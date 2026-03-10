"""
MI Orchestrator - 14개 에이전트 전체 흐름 조율

실행 순서:
Phase 1 (병렬): PMO → [뉴스, 산업, 규제, 기업] 동시 실행
Phase 2 (병렬): [시장분석, 경쟁사, 기술트렌드, 사업모델] 동시 실행
Phase 3 (순차): 인사이트 → 전략 → QA
  └─ QA 기준 미충족 시 최대 MAX_QA_RETRIES 회 재실행 (미달 Phase만)
Phase 4 (병렬): [리포트, 대시보드] 동시 실행
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import anthropic

from backend.agents.phase1.pmo_agent import PMOAgent
from backend.agents.phase1.news_agent import NewsAgent
from backend.agents.phase1.industry_data_agent import IndustryDataAgent
from backend.agents.phase1.regulatory_agent import RegulatoryAgent
from backend.agents.phase1.company_agent import CompanyAgent
from backend.agents.phase2.market_analysis_agent import MarketAnalysisAgent
from backend.agents.phase2.competitor_agent import CompetitorAgent
from backend.agents.phase2.tech_trend_agent import TechTrendAgent
from backend.agents.phase2.business_model_agent import BusinessModelAgent
from backend.agents.phase3.insight_agent import InsightAgent
from backend.agents.phase3.strategy_agent import StrategyAgent
from backend.agents.phase3.qa_agent import QAAgent, QAScore
from backend.agents.phase4.report_agent import ReportAgent
from backend.agents.phase4.dashboard_agent import DashboardAgent
from backend.models.schemas import (
    AgentContext,
    AgentOutput,
    MISession,
    QualityLevel,
    ResearchScope,
    SessionStatus,
    WSMessage,
    WSMessageType,
)

# QA 재실행 최대 횟수
MAX_QA_RETRIES = 2

# Phase별 에이전트 정의 (재실행 시 사용)
PHASE1_AGENTS = [
    ("p1_news", NewsAgent),
    ("p1_industry", IndustryDataAgent),
    ("p1_regulatory", RegulatoryAgent),
    ("p1_company", CompanyAgent),
]
PHASE2_AGENTS = [
    ("p2_market", MarketAnalysisAgent),
    ("p2_competitor", CompetitorAgent),
    ("p2_tech", TechTrendAgent),
    ("p2_bizmodel", BusinessModelAgent),
]
PHASE3_SYNTHESIS_AGENTS = [
    ("p3_insight", InsightAgent),
    ("p3_strategy", StrategyAgent),
]


class MIOrchestrator:
    """
    Market Intelligence 14-에이전트 오케스트레이터

    독립 사용 예시:
        orchestrator = MIOrchestrator(api_key="your-anthropic-key")
        scope = ResearchScope(topic="국내 핀테크 시장")
        session = await orchestrator.run(scope)
        print(session.final_report)
    """

    TOTAL_AGENTS = 14

    def __init__(self, api_key: str):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._ws_callback: Optional[Callable] = None
        self._sessions: Dict[str, MISession] = {}

    def set_ws_callback(self, callback: Callable):
        self._ws_callback = callback

    async def _send_ws(self, msg: WSMessage):
        if self._ws_callback:
            await self._ws_callback(msg)

    async def run(
        self,
        scope: ResearchScope,
        session_id: Optional[str] = None,
    ) -> MISession:
        """전체 MI 분석 실행"""
        session_id = session_id or str(uuid.uuid4())

        session = MISession(
            session_id=session_id,
            scope=scope,
            status=SessionStatus.RUNNING,
        )
        self._sessions[session_id] = session

        await self._send_ws(WSMessage(
            type=WSMessageType.LOG,
            session_id=session_id,
            message=f"MI 분석 시작: {scope.topic} (데이터 기간: {scope.date_range_days}일)",
        ))

        completed = 0

        try:
            # ── Phase 1: PMO 먼저, 나머지 병렬 ──────────────────────────
            session.current_phase = 1
            pmo_result = await self._run_agent("p1_pmo", PMOAgent, session, scope)
            session.agent_results["p1_pmo"] = pmo_result
            completed += 1
            session.progress_pct = completed / self.TOTAL_AGENTS * 100

            p1_results = await asyncio.gather(*[
                self._run_agent(aid, Cls, session, scope)
                for aid, Cls in PHASE1_AGENTS
            ], return_exceptions=True)

            for (aid, _), result in zip(PHASE1_AGENTS, p1_results):
                if isinstance(result, AgentOutput):
                    session.agent_results[aid] = result
                else:
                    await self._send_ws(WSMessage(
                        type=WSMessageType.AGENT_ERROR,
                        session_id=session_id,
                        agent_id=aid,
                        message=str(result),
                    ))
            completed += len(PHASE1_AGENTS)
            session.progress_pct = completed / self.TOTAL_AGENTS * 100

            await self._send_ws(WSMessage(
                type=WSMessageType.PHASE_COMPLETE,
                session_id=session_id,
                phase=1,
                progress_pct=session.progress_pct,
                message="Phase 1 완료 (데이터 수집)",
            ))

            # ── Phase 2: 병렬 ─────────────────────────────────────────
            session.current_phase = 2
            p2_results = await asyncio.gather(*[
                self._run_agent(aid, Cls, session, scope)
                for aid, Cls in PHASE2_AGENTS
            ], return_exceptions=True)

            for (aid, _), result in zip(PHASE2_AGENTS, p2_results):
                if isinstance(result, AgentOutput):
                    session.agent_results[aid] = result
                else:
                    await self._send_ws(WSMessage(
                        type=WSMessageType.AGENT_ERROR,
                        session_id=session_id,
                        agent_id=aid,
                        message=str(result),
                    ))
            completed += len(PHASE2_AGENTS)
            session.progress_pct = completed / self.TOTAL_AGENTS * 100

            await self._send_ws(WSMessage(
                type=WSMessageType.PHASE_COMPLETE,
                session_id=session_id,
                phase=2,
                progress_pct=session.progress_pct,
                message="Phase 2 완료 (심층 분석)",
            ))

            # ── Phase 3: Insight → Strategy → QA (+ 재실행 루프) ─────
            session.current_phase = 3

            # Insight, Strategy 순차
            for aid, Cls in PHASE3_SYNTHESIS_AGENTS:
                result = await self._run_agent(aid, Cls, session, scope)
                session.agent_results[aid] = result
                completed += 1
                session.progress_pct = completed / self.TOTAL_AGENTS * 100

            # QA + 재실행 루프
            qa_passed = False
            for attempt in range(1, MAX_QA_RETRIES + 2):  # 최초 1회 + 최대 MAX_QA_RETRIES 재실행
                qa_result = await self._run_agent("p3_qa", QAAgent, session, scope)
                session.agent_results["p3_qa"] = qa_result

                qa_passed = (
                    qa_result.quality is not None
                    and qa_result.quality.overall == QualityLevel.PASS
                )

                if qa_passed:
                    break

                if attempt <= MAX_QA_RETRIES:
                    # 미달 Phase 계산 후 재실행
                    metrics = qa_result.raw_data.get("metrics", {})
                    score = QAScore(metrics)
                    retry_phases = _get_retry_phases(score)

                    await self._send_ws(WSMessage(
                        type=WSMessageType.QA_RETRY,
                        session_id=session_id,
                        message=(
                            f"QA 기준 미충족 ({qa_result.quality.pass_rate*100:.0f}% 통과) — "
                            f"Phase {retry_phases} 재실행 중... (시도 {attempt}/{MAX_QA_RETRIES})"
                        ),
                        data={
                            "attempt": attempt,
                            "max_retries": MAX_QA_RETRIES,
                            "retry_phases": retry_phases,
                            "qa_score": qa_result.quality.pass_rate,
                        },
                    ))

                    # 미달 Phase 재실행
                    if 1 in retry_phases:
                        p1_retry = await asyncio.gather(*[
                            self._run_agent(aid, Cls, session, scope)
                            for aid, Cls in PHASE1_AGENTS
                        ], return_exceptions=True)
                        for (aid, _), r in zip(PHASE1_AGENTS, p1_retry):
                            if isinstance(r, AgentOutput):
                                session.agent_results[aid] = r

                    if 2 in retry_phases:
                        p2_retry = await asyncio.gather(*[
                            self._run_agent(aid, Cls, session, scope)
                            for aid, Cls in PHASE2_AGENTS
                        ], return_exceptions=True)
                        for (aid, _), r in zip(PHASE2_AGENTS, p2_retry):
                            if isinstance(r, AgentOutput):
                                session.agent_results[aid] = r

                    if 3 in retry_phases:
                        for aid, Cls in PHASE3_SYNTHESIS_AGENTS:
                            r = await self._run_agent(aid, Cls, session, scope)
                            session.agent_results[aid] = r
                else:
                    await self._send_ws(WSMessage(
                        type=WSMessageType.LOG,
                        session_id=session_id,
                        message=(
                            f"QA 최대 재실행 횟수({MAX_QA_RETRIES})를 초과했습니다. "
                            f"현재 점수({qa_result.quality.pass_rate*100:.0f}%)로 Phase 4를 진행합니다."
                        ),
                    ))

            completed += 1  # QA 에이전트 카운트
            session.progress_pct = completed / self.TOTAL_AGENTS * 100

            await self._send_ws(WSMessage(
                type=WSMessageType.PHASE_COMPLETE,
                session_id=session_id,
                phase=3,
                progress_pct=session.progress_pct,
                message=f"Phase 3 완료 (종합 & 인사이트) — QA {'통과' if qa_passed else '조건부 통과'}",
            ))

            # ── Phase 4: Report + Dashboard 병렬 ─────────────────────
            session.current_phase = 4
            p4_agents = [("p4_report", ReportAgent), ("p4_dashboard", DashboardAgent)]
            p4_results = await asyncio.gather(*[
                self._run_agent(aid, Cls, session, scope)
                for aid, Cls in p4_agents
            ], return_exceptions=True)

            for (aid, _), result in zip(p4_agents, p4_results):
                if isinstance(result, AgentOutput):
                    session.agent_results[aid] = result
                else:
                    await self._send_ws(WSMessage(
                        type=WSMessageType.AGENT_ERROR,
                        session_id=session_id,
                        agent_id=aid,
                        message=str(result),
                    ))
            completed += len(p4_agents)
            session.progress_pct = completed / self.TOTAL_AGENTS * 100

            await self._send_ws(WSMessage(
                type=WSMessageType.PHASE_COMPLETE,
                session_id=session_id,
                phase=4,
                progress_pct=session.progress_pct,
                message="Phase 4 완료 (리포트 & 대시보드)",
            ))

            # ── 최종 결과 추출 ──────────────────────────────────────────
            if "p4_report" in session.agent_results:
                session.final_report = session.agent_results["p4_report"].analysis
                session.executive_summary = session.agent_results["p4_report"].summary

            if "p4_dashboard" in session.agent_results:
                dashboard_agent = DashboardAgent()
                session.dashboard_data = dashboard_agent.get_dashboard_config(
                    session.agent_results["p4_dashboard"].raw_data
                )

            session.total_tokens_used = sum(
                o.tokens_used for o in session.agent_results.values()
            )

            session.status = SessionStatus.COMPLETED
            session.completed_at = datetime.utcnow()

            await self._send_ws(WSMessage(
                type=WSMessageType.SESSION_COMPLETE,
                session_id=session_id,
                progress_pct=100.0,
                message="MI 분석 완료",
                data={
                    "total_agents": len(session.agent_results),
                    "final_report_length": len(session.final_report or ""),
                    "qa_passed": qa_passed,
                    "total_tokens": session.total_tokens_used,
                },
            ))

        except asyncio.CancelledError:
            session.status = SessionStatus.CANCELLED
            raise

        except Exception as e:
            session.status = SessionStatus.FAILED
            await self._send_ws(WSMessage(
                type=WSMessageType.LOG,
                session_id=session_id,
                message=f"오케스트레이터 오류: {e}",
            ))

        return session

    async def _run_agent(
        self,
        agent_id: str,
        AgentClass,
        session: MISession,
        scope: ResearchScope,
    ) -> AgentOutput:
        """단일 에이전트 실행"""
        agent = AgentClass()
        agent.set_client(self._client)
        session.current_agent = agent_id

        async def progress_cb(a_id: str, message: str, progress: float):
            await self._send_ws(WSMessage(
                type=WSMessageType.AGENT_PROGRESS,
                session_id=session.session_id,
                agent_id=a_id,
                agent_name=agent.AGENT_NAME,
                progress_pct=progress * 100,
                message=message,
            ))

        agent.set_progress_callback(progress_cb)

        await self._send_ws(WSMessage(
            type=WSMessageType.AGENT_START,
            session_id=session.session_id,
            agent_id=agent_id,
            agent_name=agent.AGENT_NAME,
            phase=agent.PHASE.value,
            message=f"{agent.AGENT_NAME} 시작",
        ))

        context = AgentContext(
            session_id=session.session_id,
            scope=scope,
            previous_results=dict(session.agent_results),
        )

        output = await agent.run(context)

        await self._send_ws(WSMessage(
            type=WSMessageType.AGENT_COMPLETE,
            session_id=session.session_id,
            agent_id=agent_id,
            agent_name=agent.AGENT_NAME,
            message=f"{agent.AGENT_NAME} 완료 ({output.status.value})",
            data={
                "summary": output.summary,
                "data_points": output.data_points_collected,
                "quality": output.quality.overall.value if output.quality else "unknown",
                "duration": output.duration_seconds,
            },
        ))

        return output

    def get_session(self, session_id: str) -> Optional[MISession]:
        return self._sessions.get(session_id)

    def get_all_agent_specs(self) -> List[Dict]:
        """UI에 표시할 에이전트 전체 명세 반환"""
        agents = [
            PMOAgent(), NewsAgent(), IndustryDataAgent(), RegulatoryAgent(), CompanyAgent(),
            MarketAnalysisAgent(), CompetitorAgent(), TechTrendAgent(), BusinessModelAgent(),
            InsightAgent(), StrategyAgent(), QAAgent(),
            ReportAgent(), DashboardAgent(),
        ]
        return [a.get_spec() for a in agents]


def _get_retry_phases(score: QAScore) -> List[int]:
    """QA 미달 점수 기반으로 재실행 필요 Phase 목록 반환"""
    retry = set()
    if not score.data_points_ok:
        retry.update([1, 2])
    if not score.agent_pass_rate_ok:
        retry.update([1, 2])
    if not score.avg_length_ok:
        retry.update([2, 3])
    if not score.sources_ok:
        retry.add(1)
    if not score.quantitative_rate_ok:
        retry.update([1, 2])
    return sorted(retry)
