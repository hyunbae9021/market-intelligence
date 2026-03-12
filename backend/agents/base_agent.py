"""
BaseAgent - 모든 MI 에이전트의 공통 추상 클래스

설계 원칙:
1. 각 에이전트는 독립적으로 import/실행 가능
2. 표준 인터페이스(run, validate)로 통합 에이전트에 조합 가능
3. 품질 기준이 에이전트 내부에 내장됨
4. Claude API를 통해 일관된 분석 품질 보장
"""
from __future__ import annotations

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import anthropic

from backend.models.schemas import (
    AgentContext,
    AgentOutput,
    AgentPhase,
    AgentStatus,
    QualityCheck,
    QualityLevel,
    QualityReport,
)


class BaseAgent(ABC):
    """
    모든 MI 에이전트의 기반 클래스.

    사용 예시 (독립 실행):
        agent = NewsAgent()
        context = AgentContext(session_id="test", scope=ResearchScope(topic="핀테크"))
        output = await agent.run(context)

    사용 예시 (통합 에이전트):
        from backend.agents.phase1.news_agent import NewsAgent
        agents = [NewsAgent(), IndustryDataAgent()]
        results = await asyncio.gather(*[a.run(ctx) for a in agents])
    """

    # ── 에이전트 메타데이터 (하위 클래스에서 반드시 설정) ──
    AGENT_ID: str = ""          # 고유 ID (예: "p1_news")
    AGENT_NAME: str = ""        # 표시명 (예: "뉴스 & 미디어 모니터링 Agent")
    PHASE: AgentPhase = AgentPhase.PHASE1_COLLECTION

    # 엑셀 스펙에서 추출한 메타데이터
    ROLE: str = ""              # 역할
    TASKS: List[str] = []       # 주요 업무
    OUTPUT_TYPES: List[str] = [] # 결과물
    QUALITY_CRITERIA: List[str] = []  # 품질 기준
    DATA_SOURCES: List[str] = []      # 데이터 소스
    API_TOOLS: List[str] = []         # API 도구

    def __init__(self, client: Optional[anthropic.AsyncAnthropic] = None):
        self._client = client
        self._progress_callback: Optional[Callable] = None

    def set_client(self, client: anthropic.AsyncAnthropic):
        """Claude 클라이언트 주입"""
        self._client = client

    def set_progress_callback(self, callback: Callable):
        """WebSocket 진행 상황 콜백 설정"""
        self._progress_callback = callback

    async def _notify(self, message: str, progress: float = 0.0):
        """진행 상황 알림"""
        if self._progress_callback:
            await self._progress_callback(self.AGENT_ID, message, progress)

    # ── 추상 메서드 (하위 클래스 구현 필수) ──

    @abstractmethod
    async def collect_data(self, context: AgentContext) -> Dict[str, Any]:
        """
        외부 API에서 데이터 수집.
        반환값은 raw_data로 AgentOutput에 포함됨.
        """
        ...

    @abstractmethod
    async def analyze(self, context: AgentContext, raw_data: Dict[str, Any]) -> str:
        """
        Claude API를 활용한 분석.
        반환값은 Markdown 형식의 분석 결과.
        """
        ...

    # ── 기본 제공 메서드 ──

    async def run(self, context: AgentContext) -> AgentOutput:
        """
        에이전트 실행 진입점.
        collect_data → analyze → validate 순으로 실행.
        """
        started_at = datetime.utcnow()
        await self._notify(f"{self.AGENT_NAME} 시작", 0.0)

        output = AgentOutput(
            agent_id=self.AGENT_ID,
            agent_name=self.AGENT_NAME,
            phase=self.PHASE,
            status=AgentStatus.RUNNING,
            started_at=started_at,
            summary="",
        )

        try:
            # 1단계: 데이터 수집
            await self._notify("데이터 수집 중...", 0.2)
            raw_data = await self.collect_data(context)
            output.raw_data = raw_data
            output.data_points_collected = self._count_data_points(raw_data)
            output.sources_used = self._extract_sources(raw_data)

            # 2단계: Claude 분석
            await self._notify("AI 분석 중...", 0.6)
            analysis_text = await self.analyze(context, raw_data)
            output.analysis = analysis_text

            # 3단계: 요약 생성
            output.summary = await self._generate_summary(context, analysis_text)

            # 4단계: 품질 검증
            await self._notify("품질 검증 중...", 0.9)
            output.quality = await self.validate(output, context)

            output.status = AgentStatus.COMPLETED
            await self._notify(f"{self.AGENT_NAME} 완료", 1.0)

        except Exception as e:
            output.status = AgentStatus.FAILED
            output.error = str(e)
            output.summary = f"에이전트 실행 실패: {e}"
            await self._notify(f"오류 발생: {e}", 1.0)

        finally:
            output.completed_at = datetime.utcnow()
            output.duration_seconds = (
                output.completed_at - output.started_at
            ).total_seconds()

        return output

    async def validate(self, output: AgentOutput, context: AgentContext) -> QualityReport:
        """
        품질 기준(QUALITY_CRITERIA)에 따라 산출물 검증.
        하위 클래스에서 override 가능.
        """
        checks: List[QualityCheck] = []

        # 기본 검증: 데이터 수집 여부
        checks.append(QualityCheck(
            criterion="데이터 수집 성공",
            target="1개 이상",
            actual=f"{output.data_points_collected}개",
            level=QualityLevel.PASS if output.data_points_collected > 0 else QualityLevel.FAIL,
        ))

        # 기본 검증: 분석 내용 존재
        analysis_length = len(output.analysis or "")
        checks.append(QualityCheck(
            criterion="분석 내용 충분성",
            target="500자 이상",
            actual=f"{analysis_length}자",
            level=QualityLevel.PASS if analysis_length >= 500 else QualityLevel.WARNING,
        ))

        # 기본 검증: 소스 다양성
        source_count = len(output.sources_used)
        checks.append(QualityCheck(
            criterion="출처 다양성",
            target="2개 이상",
            actual=f"{source_count}개",
            level=QualityLevel.PASS if source_count >= 2 else QualityLevel.WARNING,
        ))

        pass_count = sum(1 for c in checks if c.level == QualityLevel.PASS)
        pass_rate = pass_count / len(checks) if checks else 0.0
        overall = (
            QualityLevel.PASS if pass_rate >= 0.8
            else QualityLevel.WARNING if pass_rate >= 0.5
            else QualityLevel.FAIL
        )

        return QualityReport(
            overall=overall,
            checks=checks,
            pass_rate=pass_rate,
            summary=f"{len(checks)}개 항목 중 {pass_count}개 통과 ({pass_rate*100:.0f}%)",
        )

    async def _claude(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8192,
    ) -> str:
        """Claude API 호출 공통 메서드 (streaming)"""
        if not self._client:
            return "[Claude API 키가 설정되지 않았습니다. .env 파일에 ANTHROPIC_API_KEY를 설정해주세요.]"

        chunks: list[str] = []
        chunk_count = 0
        async with self._client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            async for text in stream.text_stream:
                chunks.append(text)
                chunk_count += 1
                # 200 청크마다 Streamlit WebSocket에 keepalive 업데이트 전송
                # (스트리밍 중 연결이 끊기지 않도록)
                if chunk_count % 200 == 0:
                    total_chars = sum(len(c) for c in chunks)
                    await self._notify(f"AI 생성 중... ({total_chars:,}자 완료)", 0.5)
        return "".join(chunks)

    async def _generate_summary(self, context: AgentContext, analysis: str) -> str:
        """분석 결과에서 핵심 요약 생성"""
        system = (
            "당신은 Market Intelligence 전문가입니다. "
            "분석 결과를 3~5문장으로 핵심만 요약하세요. 반드시 한국어로 작성하세요."
        )
        prompt = f"""
리서치 주제: {context.scope.topic}
에이전트: {self.AGENT_NAME}

다음 분석 결과를 3~5문장으로 요약하세요:
{analysis[:3000]}
"""
        return await self._claude(system, prompt, max_tokens=1024)

    def _count_data_points(self, raw_data: Dict[str, Any]) -> int:
        """수집된 데이터 포인트 수 계산"""
        count = 0
        for v in raw_data.values():
            if isinstance(v, list):
                count += len(v)
            elif isinstance(v, dict):
                count += len(v)
            elif v is not None:
                count += 1
        return count

    def _extract_sources(self, raw_data: Dict[str, Any]) -> List[str]:
        """raw_data에서 소스 목록 추출"""
        sources = set()
        for key in raw_data:
            if "source" in key.lower() or "from" in key.lower():
                v = raw_data[key]
                if isinstance(v, str):
                    sources.add(v)
                elif isinstance(v, list):
                    sources.update(str(s) for s in v)
        return list(sources) if sources else list(raw_data.keys())[:3]

    def get_spec(self) -> Dict[str, Any]:
        """에이전트 명세 반환 (UI 표시용)"""
        return {
            "id": self.AGENT_ID,
            "name": self.AGENT_NAME,
            "phase": self.PHASE.value,
            "role": self.ROLE,
            "tasks": self.TASKS,
            "output_types": self.OUTPUT_TYPES,
            "quality_criteria": self.QUALITY_CRITERIA,
            "data_sources": self.DATA_SOURCES,
            "api_tools": self.API_TOOLS,
        }
