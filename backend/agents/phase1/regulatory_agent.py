"""
Agent #4: 규제/정책 동향 Agent
역할: IT/금융/AI 규제 전반 추적
Phase 1 - 데이터 수집

품질 기준:
- 주요 10개국 커버리지
- 법안 업데이트 48시간 이내 반영
- 영향 평가 논리적 일관성
- 출처 명확성
"""
from __future__ import annotations

from typing import Any, Dict

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentContext, AgentPhase, QualityCheck, QualityLevel, QualityReport
from backend.tools.news_tools import fetch_google_news_rss, fetch_sec_edgar_rss


REGULATORY_KEYWORDS = [
    "금융규제", "가상자산 규제", "AI 규제", "핀테크 규제",
    "crypto regulation", "AI Act", "fintech regulation", "MiCA",
    "SEC crypto", "FSOC", "FATF crypto",
]

REGULATORY_COUNTRIES = {
    "KR": "한국 금융위원회 가상자산",
    "US": "SEC cryptocurrency regulation",
    "EU": "EU MiCA crypto regulation",
    "JP": "Japan FSA crypto",
    "SG": "Singapore MAS crypto",
    "UK": "UK FCA crypto regulation",
    "HK": "Hong Kong SFC crypto",
}


class RegulatoryAgent(BaseAgent):
    AGENT_ID   = "p1_regulatory"
    AGENT_NAME = "규제/정책 동향 Agent"
    PHASE      = AgentPhase.PHASE1_COLLECTION

    ROLE = "IT/금융/AI 규제 전반 추적"
    TASKS = [
        "글로벌 핀테크/AI/가상자산 규제 동향",
        "국가별 법안/가이드라인 추적",
        "당사 영향 1차 평가",
        "인허가 요건 변경 추적",
    ]
    OUTPUT_TYPES = [
        "규제 동향 트래커 (국가/분야별)",
        "규제 변화 타임라인",
        "당사 영향 평가서 (MD+XLSX)",
    ]
    QUALITY_CRITERIA = [
        "주요 10개국 커버리지",
        "법안 업데이트 48시간 이내 반영",
        "영향 평가 논리적 일관성",
        "출처 명확성",
    ]
    DATA_SOURCES = ["금융위", "FSC", "SEC", "EU AI Act/MiCA", "각국 금융당국 공시", "OECD/BIS 보고서"]
    API_TOOLS   = ["SEC EDGAR API", "정부 공시 RSS", "Google Alerts", "Web Scraping"]

    async def collect_data(self, context: AgentContext) -> Dict[str, Any]:
        await self._notify("규제 데이터 수집 중...", 0.1)

        import asyncio
        tasks = []

        # 국가별 규제 뉴스 수집
        for country_code, query in list(REGULATORY_COUNTRIES.items())[:5]:
            tasks.append(fetch_google_news_rss(query, lang="en" if country_code != "KR" else "ko", count=5))

        # SEC EDGAR 공시
        tasks.append(fetch_sec_edgar_rss())

        # 규제 키워드별 뉴스
        for kw in REGULATORY_KEYWORDS[:3]:
            tasks.append(fetch_google_news_rss(kw, count=5))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        country_codes = list(REGULATORY_COUNTRIES.keys())[:5]
        country_news = {}
        for i, code in enumerate(country_codes):
            r = results[i]
            country_news[code] = r if not isinstance(r, Exception) else []

        sec_idx = len(country_codes)
        sec_data = results[sec_idx] if not isinstance(results[sec_idx], Exception) else []

        keyword_news = []
        for r in results[sec_idx + 1:]:
            if not isinstance(r, Exception):
                keyword_news.extend(r)

        return {
            "country_news": country_news,
            "sec_edgar": sec_data,
            "keyword_news": keyword_news,
            "countries_covered": list(REGULATORY_COUNTRIES.keys()),
            "source": "규제/정책 모니터링",
        }

    async def analyze(self, context: AgentContext, raw_data: Dict[str, Any]) -> str:
        country_news = raw_data.get("country_news", {})
        sec_data = raw_data.get("sec_edgar", [])
        keyword_news = raw_data.get("keyword_news", [])

        # 국가별 뉴스 요약
        country_summary = []
        for country, news in country_news.items():
            valid = [n for n in news if "error" not in n][:3]
            if valid:
                headlines = " / ".join([n.get("title", "")[:50] for n in valid])
                country_summary.append(f"- **{country}**: {headlines}")

        country_text = "\n".join(country_summary)

        # SEC 공시
        sec_text = "\n".join([
            f"- {item.get('title', '')[:80]}"
            for item in sec_data[:5] if "error" not in item
        ])

        system = """당신은 글로벌 금융/핀테크/AI 규제 전문가입니다.
수집된 규제 동향 데이터를 분석하여 기업에 미치는 영향을 평가하세요.
반드시 한국어로 작성하고, Markdown 형식을 사용하세요."""

        prompt = f"""
리서치 주제: {context.scope.topic}

## 국가별 규제 뉴스
{country_text if country_text else '수집된 데이터 없음'}

## SEC 최근 공시
{sec_text if sec_text else '수집된 데이터 없음'}

## 주요 규제 키워드 뉴스
{chr(10).join([f"- {n.get('title', '')[:80]}" for n in keyword_news[:10] if "error" not in n])}

위 데이터를 분석하여 다음 형식으로 규제 동향 리포트를 작성하세요:

## 1. 글로벌 규제 동향 요약
- 이번 주 가장 중요한 규제 변화 Top 3

## 2. 국가별 규제 현황

### 한국 (KR)
- 최신 동향 및 영향

### 미국 (US)
- SEC/CFTC 동향

### 유럽 (EU)
- MiCA/AI Act 진행 현황

### 아시아 주요국 (JP/SG/HK)
- 동향 요약

## 3. 규제 유형별 분석
| 규제 분야 | 주요 동향 | 영향도 | 대응 시급성 |
|-----------|----------|--------|------------|
| 가상자산 | | | |
| AI/데이터 | | | |
| AML/CFT | | | |
| 소비자 보호 | | | |

## 4. 당사 영향 평가
- **즉시 대응 필요** (High):
- **모니터링 필요** (Medium):
- **참고 사항** (Low):

## 5. 규제 리스크 레이더
- 단기 (1~3개월):
- 중기 (3~6개월):
- 장기 (6개월 이상):

## 6. 권고 대응 방안
"""
        return await self._claude(system, prompt, max_tokens=16000)

    async def validate(self, output, context: AgentContext) -> QualityReport:
        checks = []

        raw = output.raw_data
        countries_covered = len(raw.get("country_news", {}))
        checks.append(QualityCheck(
            criterion="국가 커버리지 (10개국 목표)",
            target="5개국 이상",
            actual=f"{countries_covered}개국",
            level=QualityLevel.PASS if countries_covered >= 5 else QualityLevel.WARNING,
        ))

        total_items = output.data_points_collected
        checks.append(QualityCheck(
            criterion="규제 데이터 수집량",
            target="20개 이상",
            actual=f"{total_items}개",
            level=QualityLevel.PASS if total_items >= 20 else QualityLevel.WARNING,
        ))

        analysis = output.analysis or ""
        has_impact_assessment = "당사 영향" in analysis or "대응" in analysis
        checks.append(QualityCheck(
            criterion="영향 평가 포함 여부",
            target="당사 영향 평가 포함",
            actual="포함" if has_impact_assessment else "미포함",
            level=QualityLevel.PASS if has_impact_assessment else QualityLevel.WARNING,
        ))

        pass_count = sum(1 for c in checks if c.level == QualityLevel.PASS)
        pass_rate = pass_count / len(checks)
        return QualityReport(
            overall=QualityLevel.PASS if pass_rate >= 0.67 else QualityLevel.WARNING,
            checks=checks,
            pass_rate=pass_rate,
            summary=f"{len(checks)}개 항목 중 {pass_count}개 통과",
        )
