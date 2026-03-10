"""
Agent #2: 뉴스 & 미디어 모니터링 Agent
역할: IT/금융/테크 뉴스 전반 크롤링
Phase 1 - 데이터 수집

품질 기준:
- 주요 매체 커버리지 90%+
- 분류 정확도 85%+
- 실시간성 (30분 이내)
- 감성 분석 오차율 <15%
"""
from __future__ import annotations

from typing import Any, Dict

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentContext, AgentPhase, QualityCheck, QualityLevel, QualityReport
from backend.tools.news_tools import gather_news


class NewsAgent(BaseAgent):
    AGENT_ID   = "p1_news"
    AGENT_NAME = "뉴스 & 미디어 모니터링 Agent"
    PHASE      = AgentPhase.PHASE1_COLLECTION

    ROLE = "IT/금융/테크 뉴스 전반 크롤링"
    TASKS = [
        "글로벌 IT/핀테크/AI/블록체인 뉴스 수집",
        "키워드 기반 필터링/분류",
        "긍/부정 감성 분석",
        "주요 이슈 실시간 알림",
    ]
    OUTPUT_TYPES = [
        "주간 뉴스 클리핑 리포트",
        "감성 분석 대시보드",
        "이슈 알림 로그 (MD+XLSX)",
    ]
    QUALITY_CRITERIA = [
        "주요 매체 커버리지 90%+",
        "분류 정확도 85%+",
        "실시간성 (30분 이내)",
        "감성 분석 오차율 <15%",
    ]
    DATA_SOURCES = [
        "TechCrunch", "The Information",
        "CoinDesk", "The Block",
        "블로터", "디지털데일리",
        "트위터/X", "Reddit",
    ]
    API_TOOLS = ["Google News API", "Twitter/X API", "CryptoPanic API", "Feedly API"]

    async def collect_data(self, context: AgentContext) -> Dict[str, Any]:
        scope = context.scope
        await self._notify("뉴스 소스 수집 중...", 0.1)

        # 영어/한국어 쿼리 생성
        topic = scope.topic
        industries = scope.industries or ["AI", "fintech", "crypto", "blockchain"]
        crypto_currencies = "BTC,ETH,BNB"

        data = await gather_news(
            topic=topic,
            crypto_currencies=crypto_currencies,
        )

        # 추가 산업별 뉴스
        for industry in industries[:2]:
            industry_news = await gather_news(topic=f"{topic} {industry}")
            data[f"industry_{industry}"] = industry_news.get("google_news_ko", [])

        return data

    async def analyze(self, context: AgentContext, raw_data: Dict[str, Any]) -> str:
        # 뉴스 항목 취합
        all_news = []
        for key, items in raw_data.items():
            if isinstance(items, list):
                all_news.extend(items[:10])

        # 에러 제외
        valid_news = [n for n in all_news if "error" not in n]

        system = """당신은 Market Intelligence 뉴스 분석 전문가입니다.
분석 원칙:
- 모든 주요 주장에는 구체적 수치(시장규모, 성장률, 기업가치, 점유율 등)를 반드시 포함하세요
- 각 데이터에는 출처를 명시하세요 (예: "출처: CoinDesk, 2025.03")
- 핵심 인사이트는 별도 인용구 형태("...")로 강조하세요
- 비교 분석 시에는 표 형식을 사용하세요
- 수치 없는 일반적 서술은 지양하고, 측정 가능한 사실 위주로 작성하세요
반드시 한국어로 작성하고, Markdown 형식을 사용하세요."""

        news_text = "\n".join([
            f"- [{n.get('source', '')}] {n.get('title', '')} | {n.get('summary', '')[:150]}"
            for n in valid_news[:50]
        ])

        date_range = context.scope.date_range_days

        prompt = f"""
리서치 주제: {context.scope.topic}
수집 기간: 최근 {date_range}일
수집된 뉴스 기사 수: {len(valid_news)}개

## 수집된 뉴스
{news_text}

위 뉴스를 분석하여 다음 형식의 심층 리포트를 작성하세요.
**수치와 출처 없는 문장은 작성하지 마세요.**

---

## 핵심 요약
> (1-2문장으로 이번 기간 가장 중요한 시장 변화를 수치와 함께 요약)

## 1. 핵심 이슈 분석 (TOP 5)

각 이슈에 대해 아래 형식으로 작성:
### 이슈 1: [이슈명]
- **핵심 주장**: (1문장, 수치 포함)
- **주요 내용**: (구체적 수치, 기업명, 날짜 포함)
- **관련 기사 수**: X건
- **감성**: 긍정/부정/중립 (근거 포함)
- **시사점**: (사업적 의미)

## 2. 분야별 동향 분류

| 분야 | 주요 이슈 | 핵심 수치 | 감성 | 출처 |
|------|---------|---------|------|------|
| AI/기술 | | | | |
| 금융/핀테크 | | | | |
| 블록체인/크립토 | | | | |
| 규제/정책 | | | | |

## 3. 감성 분석

| 구분 | 건수 | 비중(%) | 대표 이슈 |
|------|------|---------|---------|
| 긍정 | | | |
| 중립 | | | |
| 부정 | | | |

**"** (핵심 긍정 시그널 인사이트) **"**
**"** (핵심 부정 리스크 인사이트) **"**

## 4. 주목 트렌드 (최근 {date_range}일)

각 트렌드에 대해:
- **트렌드명**:
- **관련 기사 수 및 기간**:
- **핵심 데이터**: (시장 규모, 성장률, 투자 금액 등 수치)
- **주요 기업/기관**:
- **향후 전망**: (수치 기반)

## 5. 사업 기회 및 리스크 매트릭스

| 구분 | 내용 | 예상 영향도 | 대응 시급성 |
|------|------|-----------|-----------|
| 기회 1 | | 상/중/하 | 상/중/하 |
| 기회 2 | | | |
| 리스크 1 | | | |
| 리스크 2 | | | |

## 6. 모니터링 권고 항목
- 단기 (1개월):
- 중기 (3개월):
- 장기 (6개월+):
"""
        return await self._claude(system, prompt, max_tokens=4000)

    async def validate(self, output, context: AgentContext) -> QualityReport:
        checks = []

        # 수집된 뉴스 수
        total_news = output.data_points_collected
        checks.append(QualityCheck(
            criterion="뉴스 기사 수집량",
            target="20개 이상",
            actual=f"{total_news}개",
            level=QualityLevel.PASS if total_news >= 20 else QualityLevel.WARNING,
        ))

        # 소스 다양성
        source_count = len(output.sources_used)
        checks.append(QualityCheck(
            criterion="출처 다양성 (주요 매체 커버리지)",
            target="3개 이상 소스",
            actual=f"{source_count}개 소스",
            level=QualityLevel.PASS if source_count >= 3 else QualityLevel.WARNING,
        ))

        # 분석 내용 충분성
        analysis_len = len(output.analysis or "")
        checks.append(QualityCheck(
            criterion="감성 분석 포함 여부",
            target="분석 내용 1000자 이상",
            actual=f"{analysis_len}자",
            level=QualityLevel.PASS if analysis_len >= 1000 else QualityLevel.WARNING,
        ))

        # 한국어/영어 뉴스 균형
        raw = output.raw_data
        ko_count = len(raw.get("google_news_ko", []))
        en_count = len(raw.get("google_news_en", []))
        checks.append(QualityCheck(
            criterion="한국어/영어 뉴스 균형",
            target="각 5개 이상",
            actual=f"한국어 {ko_count}개, 영어 {en_count}개",
            level=QualityLevel.PASS if ko_count >= 5 and en_count >= 5 else QualityLevel.WARNING,
        ))

        pass_count = sum(1 for c in checks if c.level == QualityLevel.PASS)
        pass_rate = pass_count / len(checks)
        overall = (
            QualityLevel.PASS if pass_rate >= 0.75
            else QualityLevel.WARNING if pass_rate >= 0.5
            else QualityLevel.FAIL
        )

        return QualityReport(
            overall=overall,
            checks=checks,
            pass_rate=pass_rate,
            summary=f"{len(checks)}개 항목 중 {pass_count}개 통과",
        )
