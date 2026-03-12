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

        system = """당신은 두나무 경영혁신실 소속 가상자산 업계 뉴스 분석 전문가입니다.
분석 원칙:
- 7일 이내 기사만 포함하세요. 기간 초과 기사는 제외하세요.
- 출처(언론사·날짜)를 반드시 명시하세요.
- 동일 사안은 1건만 대표 노출하세요 (Tier 1 > Tier 2 > Tier 3).
- 주요 뉴스(재무·규제·사업)는 별도 섹션에 먼저 정리하세요.
- 요약은 2줄 이내로 핵심만 기술하세요.
- 기사가 없는 탭은 "해당 기간 기사 없음"으로 명시하세요.
- 두나무/경쟁 구도 관련 함의를 주요 뉴스에 한 줄 덧붙이세요.

언론사 Tier 기준:
- Tier 1 국내 종합: 조선일보, 중앙일보, 동아일보, 한국경제, 매일경제, 서울경제
- Tier 1 국내 경제·금융: 이데일리, 머니투데이, 파이낸셜뉴스, 한국금융신문
- Tier 1 국내 크립토: 코인데스크코리아, 블록미디어, 디센터, 토큰포스트
- Tier 1 해외 주요: Reuters, Bloomberg, WSJ, Financial Times
- Tier 1 해외 크립토: CoinDesk, The Block, Decrypt, CoinTelegraph
- Tier 2 리서치: 4Pillars, Tiger Research, Xangle, Messari, Delphi Digital, a16z Crypto
- Tier 3: 위 이외 매체

주요 뉴스 유형:
- 💰 재무: 상장(IPO), 신규 투자 유치, 펀딩, 어닝 서프라이즈, 실적 미달, 영업이익·매출 급변
- ⚖️ 규제·법무: 규제 리스크, 신규 규제 입법·시행, 소송·기소·제재, 영업정지, VASP·라이선스 이슈
- 🚀 사업: 신사업·신기능 런칭, 서비스 출시, 파트너십·제휴, M&A·인수합병

반드시 한국어로 작성하고, Markdown 형식을 사용하세요."""

        news_text = "\n".join([
            f"- [{n.get('source', '')}] {n.get('title', '')} | {n.get('summary', '')[:150]}"
            for n in valid_news[:50]
        ])

        import datetime
        today = datetime.date.today()
        week_ago = today - datetime.timedelta(days=7)

        prompt = f"""
리서치 주제: {context.scope.topic}
기준일: {today.strftime('%Y-%m-%d')}
수집 기간: {week_ago.strftime('%Y-%m-%d')} ~ {today.strftime('%Y-%m-%d')} (7일)
수집된 뉴스 기사 수: {len(valid_news)}개

## 수집된 뉴스
{news_text}

위 뉴스를 분석하여 아래 형식의 주간 뉴스 클리핑 리포트를 작성하세요.

---

# 주간 뉴스 클리핑
**기준일:** {today.strftime('%Y-%m-%d')}
**수집 기간:** {week_ago.strftime('%Y-%m-%d')} ~ {today.strftime('%Y-%m-%d')} (1주)

---

## ⚡ 이번 주 주요 뉴스
> 재무·규제·사업 유형에 해당하는 기사만 포함. 해당 없으면 섹션 생략.

1. [💰/⚖️/🚀] **[제목]** — [출처] (YYYY-MM-DD)
   - [요약 1줄]
   - [두나무/경쟁 구도에 주는 함의 1줄]

---

## 1. 국내 가상자산 시장

### 규제
| 날짜 | 제목 | 출처 | 요약 |
|------|------|------|------|
| MM-DD | [제목] | [언론사] | [2줄 이내] |

### 시장
(동일 형식)

### 경쟁사 (빗썸·코빗·고팍스)
(동일 형식)

### 두나무·업비트
(동일 형식)

---

## 2. 글로벌 거래소

### Coinbase
(동일 형식)

### Binance
(동일 형식)

### OKX / Kraken / Bybit
(동일 형식)

---

## 3. 트렌드 F/U

### 결제 (스테이블코인·온체인)
(동일 형식)

### DEX
(동일 형식)

### 예측시장
(동일 형식)

### AI × 크립토
(동일 형식)

### 핀테크·디지털금융
(동일 형식)

---

## 편집 주석
- 수집 건수: [총 N건]
- 주요 뉴스 해당: [N건]
- 정보 공백 (기사 없음): [해당 탭 명시]
"""
        return await self._claude(system, prompt, max_tokens=8000)

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
