"""
Agent #5: 기업/스타트업 정보 수집 Agent
역할: 경쟁사 및 유망 기업 정보 모니터링
Phase 1 - 데이터 수집

품질 기준:
- 주요 기업 커버리지
- 공시 24시간 이내 반영
- 밸류에이션 교차 검증
- 데이터 정확성 95%+
"""
from __future__ import annotations

from typing import Any, Dict

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentContext, AgentPhase, QualityCheck, QualityLevel, QualityReport
from backend.tools.company_tools import gather_company_data
from backend.tools.news_tools import fetch_google_news_rss


class CompanyAgent(BaseAgent):
    AGENT_ID   = "p1_company"
    AGENT_NAME = "기업/스타트업 정보 수집 Agent"
    PHASE      = AgentPhase.PHASE1_COLLECTION

    ROLE = "경쟁사 및 유망 기업 정보 모니터링"
    TASKS = [
        "동종업계 기업 공시/IR/어닝콜 모니터링",
        "투자 라운드/밸류에이션 추적",
        "인사/조직 변화 추적",
        "파트너십/M&A 현황 수집",
    ]
    OUTPUT_TYPES = [
        "기업 프로파일 DB",
        "투자/파트너십 트래커",
        "경쟁사 IR 요약 (XLSX+DB)",
    ]
    QUALITY_CRITERIA = [
        "주요 기업 커버리지",
        "공시 24시간 이내 반영",
        "밸류에이션 교차 검증",
        "데이터 정확성 95%+",
    ]
    DATA_SOURCES = [
        "SEC EDGAR", "DART/KIND",
        "Crunchbase", "The VC", "혁신의 숲",
        "기업 IR 페이지", "LinkedIn", "Glassdoor",
    ]
    API_TOOLS = ["DART API", "SEC EDGAR API", "Crunchbase API", "PitchBook API"]

    async def collect_data(self, context: AgentContext) -> Dict[str, Any]:
        await self._notify("기업 정보 수집 중...", 0.1)

        scope = context.scope
        target_companies = scope.target_companies or []

        import asyncio

        # 기업 데이터 수집
        company_data = await gather_company_data(
            target_companies=target_companies,
        )

        # 경쟁사 뉴스 수집
        company_news_tasks = []
        for company in (target_companies or ["Coinbase", "Binance", "Upbit"])[:3]:
            company_news_tasks.append(
                fetch_google_news_rss(f"{company} IR 투자 M&A", lang="ko", count=5)
            )
            company_news_tasks.append(
                fetch_google_news_rss(f"{company} funding acquisition", lang="en", count=5)
            )

        news_results = await asyncio.gather(*company_news_tasks, return_exceptions=True)
        company_news = []
        for r in news_results:
            if not isinstance(r, Exception):
                company_news.extend(r)

        company_data["company_news"] = company_news
        return company_data

    async def analyze(self, context: AgentContext, raw_data: Dict[str, Any]) -> str:
        exchanges = raw_data.get("exchanges", [])[:10]
        github_orgs = raw_data.get("github_orgs", [])
        company_news = raw_data.get("company_news", [])[:20]

        exchange_text = "\n".join([
            f"- {ex.get('name', '')} ({ex.get('country', '')}): "
            f"24h 거래량 {ex.get('volume_24h_btc', 0):.0f} BTC, "
            f"신뢰점수 {ex.get('trust_score', 0)}/10"
            for ex in exchanges if "error" not in ex
        ])

        news_text = "\n".join([
            f"- [{n.get('source', '')}] {n.get('title', '')[:80]}"
            for n in company_news if "error" not in n
        ])

        system = """당신은 Market Intelligence 기업 분석 전문가입니다.
수집된 기업 정보를 분석하여 경쟁 구도와 주요 동향을 파악하세요.
반드시 한국어로 작성하고, Markdown 형식을 사용하세요."""

        prompt = f"""
리서치 주제: {context.scope.topic}
분석 대상 기업: {', '.join(context.scope.target_companies) if context.scope.target_companies else '크립토 거래소 전반'}

## 글로벌 주요 거래소 현황
{exchange_text if exchange_text else '데이터 없음'}

## 기업 관련 최신 뉴스
{news_text if news_text else '데이터 없음'}

위 데이터를 분석하여 다음 형식으로 기업 동향 리포트를 작성하세요:

## 1. 경쟁 구도 개요
- 글로벌 주요 플레이어 현황
- 시장 점유율 추정
- 경쟁 강도 평가

## 2. 주요 기업별 동향
각 주요 기업에 대해:
- 최신 주요 이슈
- 전략적 움직임
- 주목할 변화

## 3. 투자/M&A 동향
- 최근 주요 딜 현황
- 투자 트렌드 분석
- 주목할 스타트업

## 4. 기술/제품 경쟁력 분석
- 주요 기업별 기술 차별화 포인트
- 신규 서비스/기능 출시 현황

## 5. 인사/조직 변화
- 주요 C-레벨 변동
- 채용 트렌드 (확장/축소 여부)

## 6. 당사 관점 경쟁 시사점
- 위협 요인
- 벤치마킹 대상
- 협력 가능 영역

## 7. 기업 프로파일 요약표
| 기업명 | 국가 | 강점 | 최근 동향 | 위협도 |
|--------|------|------|----------|--------|
"""
        return await self._claude(system, prompt, max_tokens=3000)

    async def validate(self, output, context: AgentContext) -> QualityReport:
        checks = []

        exchanges_count = len([e for e in output.raw_data.get("exchanges", []) if "error" not in e])
        checks.append(QualityCheck(
            criterion="기업 데이터 수집 수",
            target="10개사 이상",
            actual=f"{exchanges_count}개사",
            level=QualityLevel.PASS if exchanges_count >= 10 else QualityLevel.WARNING,
        ))

        news_count = len([n for n in output.raw_data.get("company_news", []) if "error" not in n])
        checks.append(QualityCheck(
            criterion="기업 관련 뉴스 수집",
            target="10개 이상",
            actual=f"{news_count}개",
            level=QualityLevel.PASS if news_count >= 10 else QualityLevel.WARNING,
        ))

        analysis = output.analysis or ""
        has_competitive = "경쟁" in analysis and "시사점" in analysis
        checks.append(QualityCheck(
            criterion="경쟁 분석 포함 여부",
            target="경쟁 구도 및 시사점 포함",
            actual="포함" if has_competitive else "미포함",
            level=QualityLevel.PASS if has_competitive else QualityLevel.WARNING,
        ))

        pass_count = sum(1 for c in checks if c.level == QualityLevel.PASS)
        pass_rate = pass_count / len(checks)
        return QualityReport(
            overall=QualityLevel.PASS if pass_rate >= 0.67 else QualityLevel.WARNING,
            checks=checks,
            pass_rate=pass_rate,
            summary=f"{len(checks)}개 항목 중 {pass_count}개 통과",
        )
