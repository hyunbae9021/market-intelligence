"""
Agent #8: 기술 트렌드 분석 Agent
역할: AI/블록체인/핀테크 등 기술 동향 분석
Phase 2 - 분석 & 심층 리서치
"""
from __future__ import annotations

from typing import Any, Dict

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentContext, AgentPhase, QualityCheck, QualityLevel, QualityReport
from backend.tools.tech_tools import gather_tech_data


class TechTrendAgent(BaseAgent):
    AGENT_ID   = "p2_tech"
    AGENT_NAME = "기술 트렌드 분석 Agent"
    PHASE      = AgentPhase.PHASE2_ANALYSIS

    ROLE = "AI/블록체인/핀테크 등 기술 동향 분석"
    TASKS = [
        "주요 기술 트렌드 분석 (LLM, 에이전트, DeFi, RWA 등)",
        "기술 성숙도 평가",
        "당사 적용 가능성 검토",
        "기술 로드맵 벤치마킹",
    ]
    OUTPUT_TYPES = [
        "기술 트렌드 리포트",
        "기술 비교 매트릭스",
        "기술 로드맵 분석",
        "Hype Cycle 매핑 (MD+XLSX)",
    ]
    QUALITY_CRITERIA = [
        "기술 정확성 검증",
        "주요 트렌드 20개+ 커버",
        "최신 논문/발표 반영",
        "객관적 평가 기준 적용",
    ]
    DATA_SOURCES = ["GitHub 리포지토리", "ArXiv/논문", "프로토콜 공식 문서", "Gartner Hype Cycle"]
    API_TOOLS   = ["GitHub API", "ArXiv API", "HuggingFace API", "StackOverflow API"]

    async def collect_data(self, context: AgentContext) -> Dict[str, Any]:
        await self._notify("기술 트렌드 데이터 수집 중...", 0.1)

        industries = context.scope.industries or ["AI", "blockchain", "DeFi"]
        topics = industries + ["LLM", "agent AI", "RWA"]

        data = await gather_tech_data(topics=topics[:4])

        # Phase 1 결과 추가
        if "p1_news" in context.previous_results:
            data["news_analysis"] = context.previous_results["p1_news"].analysis

        return data

    async def analyze(self, context: AgentContext, raw_data: Dict[str, Any]) -> str:
        papers = raw_data.get("arxiv_papers", [])[:15]
        github = raw_data.get("github_trending", [])[:10]
        hf_models = raw_data.get("huggingface_models", [])[:10]

        papers_text = "\n".join([
            f"- [{p.get('source', 'ArXiv')}] {p.get('title', '')[:80]}\n  요약: {p.get('summary', '')[:150]}"
            for p in papers if "error" not in p
        ])

        github_text = "\n".join([
            f"- {r.get('name', '')} ⭐{r.get('stars', 0):,} [{r.get('language', '')}]: {r.get('description', '')[:80]}"
            for r in github if "error" not in r
        ])

        hf_text = "\n".join([
            f"- {m.get('name', '')} ({m.get('task', '')}): {m.get('downloads', 0):,} downloads"
            for m in hf_models if "error" not in m
        ])

        system = """당신은 AI, 블록체인, 핀테크 분야의 기술 트렌드 전문가입니다.
최신 논문, 오픈소스 프로젝트, AI 모델 트렌드를 분석하여 Gartner Hype Cycle 관점에서 평가하세요.
기업의 기술 적용 가능성과 로드맵 시사점을 제시하세요.
반드시 한국어로 작성하고, Markdown 형식을 사용하세요."""

        prompt = f"""
리서치 주제: {context.scope.topic}
분석 산업: {', '.join(context.scope.industries or ['AI', 'blockchain', 'fintech'])}

## 최신 ArXiv 논문 (AI/기술)
{papers_text if papers_text else '데이터 없음'}

## GitHub 트렌딩 프로젝트
{github_text if github_text else '데이터 없음'}

## HuggingFace 인기 AI 모델
{hf_text if hf_text else '데이터 없음'}

위 데이터를 분석하여 기술 트렌드 리포트를 작성하세요:

## 1. 핵심 기술 트렌드 Top 10
각 트렌드:
- **트렌드명**: 설명
- **성숙도**: Innovation Trigger / Peak / Trough / Slope / Plateau
- **기업 영향도**: High/Medium/Low
- **적용 시간 지평**: 즉시/1년/2~3년

## 2. AI/LLM 트렌드 분석
- 주요 모델 및 기술 발전
- 에이전트 AI 동향
- 엔터프라이즈 AI 도입 현황
- 당사 관련 활용 방안

## 3. 블록체인/크립토 기술 동향
- Layer 1/2 기술 발전
- DeFi 프로토콜 혁신
- RWA (실물자산 토큰화) 트렌드
- 인프라 성숙도 평가

## 4. 핀테크 기술 트렌드
- 결제/송금 기술 혁신
- 임베디드 파이낸스
- 오픈뱅킹 생태계
- RegTech 발전

## 5. Gartner Hype Cycle 매핑
각 주요 기술의 현재 위치:
| 기술 | Hype Cycle 단계 | 주류 채택까지 | 당사 준비도 |
|------|----------------|-------------|-----------|

## 6. 기술 로드맵 시사점
- 단기 적용 권고 (0~6개월)
- 중기 투자 고려 (6~18개월)
- 장기 모니터링 (18개월+)

## 7. 오픈소스 생태계 분석
- 주목할 오픈소스 프로젝트
- 커뮤니티 동향
- 기업 채택 현황
"""
        return await self._claude(system, prompt, max_tokens=8192)

    async def validate(self, output, context: AgentContext) -> QualityReport:
        checks = []
        analysis = output.analysis or ""

        has_hype = "Hype Cycle" in analysis or "성숙도" in analysis
        checks.append(QualityCheck(
            criterion="Hype Cycle 분석 포함",
            target="기술 성숙도 평가 포함",
            actual="포함" if has_hype else "미포함",
            level=QualityLevel.PASS if has_hype else QualityLevel.WARNING,
        ))

        has_ai = "AI" in analysis or "LLM" in analysis
        has_blockchain = "블록체인" in analysis or "DeFi" in analysis
        checks.append(QualityCheck(
            criterion="AI/블록체인 분야 모두 커버",
            target="AI, 블록체인 분야 포함",
            actual="포함" if (has_ai and has_blockchain) else "일부 누락",
            level=QualityLevel.PASS if (has_ai and has_blockchain) else QualityLevel.WARNING,
        ))

        papers_count = len([p for p in output.raw_data.get("arxiv_papers", []) if "error" not in p])
        checks.append(QualityCheck(
            criterion="최신 논문 반영",
            target="5개 이상 논문",
            actual=f"{papers_count}개 논문",
            level=QualityLevel.PASS if papers_count >= 5 else QualityLevel.WARNING,
        ))

        pass_count = sum(1 for c in checks if c.level == QualityLevel.PASS)
        pass_rate = pass_count / len(checks)
        return QualityReport(
            overall=QualityLevel.PASS if pass_rate >= 0.67 else QualityLevel.WARNING,
            checks=checks,
            pass_rate=pass_rate,
            summary=f"{len(checks)}개 항목 중 {pass_count}개 통과",
        )
