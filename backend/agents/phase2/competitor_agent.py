"""
Agent #7: 경쟁사/동종업계 분석 Agent
역할: 주요 경쟁사 및 동종업계 심층 분석
Phase 2 - 분석 & 심층 리서치

품질 기준:
- 분석 대상 15개사 이상
- 정량/정성 균형
- 프레임워크 일관성
- 최신 데이터 기반 (3개월 이내)
"""
from __future__ import annotations

from typing import Any, Dict

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentContext, AgentPhase, QualityCheck, QualityLevel, QualityReport


class CompetitorAgent(BaseAgent):
    AGENT_ID   = "p2_competitor"
    AGENT_NAME = "경쟁사/동종업계 분석 Agent"
    PHASE      = AgentPhase.PHASE2_ANALYSIS

    ROLE = "주요 경쟁사 및 동종업계 심층 분석"
    TASKS = [
        "경쟁사 사업모델/수익구조 분석",
        "제품/서비스 비교",
        "SWOT 분석",
        "경쟁 포지셔닝 맵 작성",
    ]
    OUTPUT_TYPES = [
        "경쟁사 프로파일 심층 리포트",
        "비교 분석 매트릭스",
        "SWOT 분석표",
        "포지셔닝 맵 (MD+XLSX)",
    ]
    QUALITY_CRITERIA = [
        "분석 대상 15개사 이상",
        "정량/정성 균형",
        "프레임워크 일관성",
        "최신 데이터 기반 (3개월 이내)",
    ]
    DATA_SOURCES = ["Phase 1 기업 정보", "기업 IR/연간보고서", "업계 리서치 리포트"]
    API_TOOLS   = ["Phase 1 Agent 결과물", "LinkedIn API", "Owler API"]

    async def collect_data(self, context: AgentContext) -> Dict[str, Any]:
        prev = context.previous_results
        data = {}

        if "p1_company" in prev:
            company_output = prev["p1_company"]
            data["company_raw"] = company_output.raw_data
            data["company_analysis"] = company_output.analysis

        if "p1_news" in prev:
            data["news_analysis"] = prev["p1_news"].analysis

        data["target_companies"] = context.scope.target_companies
        data["topic"] = context.scope.topic
        return data

    async def analyze(self, context: AgentContext, raw_data: Dict[str, Any]) -> str:
        company_analysis = raw_data.get("company_analysis", "")
        exchanges = raw_data.get("company_raw", {}).get("exchanges", [])[:15]

        exchange_text = "\n".join([
            f"- {ex.get('name', '')} ({ex.get('country', '')}): "
            f"거래량 {ex.get('volume_24h_btc', 0):.0f} BTC/24h, "
            f"신뢰점수 {ex.get('trust_score', 0)}/10, "
            f"설립 {ex.get('year_established', 'N/A')}"
            for ex in exchanges if "error" not in ex
        ])

        system = """당신은 두나무 경영혁신실 소속 가상자산 업계 경쟁사 분석 전문가입니다.
핵심 원칙:
1. 수치 중심으로 서술하세요. "빠른 성장"이 아니라 "YoY +143% (2023→2024)"처럼 구체적으로.
2. 출처를 명시하세요. 공시, IR 자료, 언론, LinkedIn 등 근거를 항목 옆에 괄호로 표기.
3. 추정치는 명확히 구분하세요. 확인된 수치와 추정치를 혼용하지 말고, 추정치는 항상 "(추정)" 표기.
4. 평가표 각 셀에는 등급 + 한 줄 근거를 함께 기재하세요. 등급만 있는 셀은 무의미합니다.
5. 우리 기업(두나무/업비트)도 Player로 포함하세요.
6. 정보 공백은 "정보 없음 (비공개 추정)" 또는 "추가 조사 필요"로 표기하세요.
7. 시나리오는 Feasibility '상'인 것만 출력하세요. Feasibility '상'이 없으면 해당 섹션을 "현재 시점에서 Feasibility '상'에 해당하는 시나리오 없음"으로 표기하세요.
반드시 한국어로 작성하고, Markdown 형식을 사용하세요."""

        target_companies = context.scope.target_companies or ["Coinbase", "Binance", "OKX", "Bybit", "Upbit"]
        companies_str = ", ".join(target_companies[:10])

        prompt = f"""
리서치 주제: {context.scope.topic}
분석 대상 시장: 가상자산 거래소 시장 (국내 + 글로벌)
분석 대상 기업: {companies_str}
데이터 수집 기간: 최근 {context.scope.date_range_days}일

## 경쟁사 실시간 데이터
{exchange_text if exchange_text else '데이터 없음'}

## Phase 1 기업 분석 요약
{(company_analysis or '')[:6000]}

위 데이터를 바탕으로 아래 형식의 경쟁사 분석 리포트를 작성하세요.

---

# {context.scope.topic} 경쟁사 분석

---

## 1. Player 목록

### Domestic Players
| 우선순위 | 기업명 | 포함 근거 |
|----------|--------|-----------|
| 🔴 | 두나무 (업비트) | 국내 1위 가상자산 거래소 (분석 주체) |
| 🔴 | 빗썸 | 국내 2위 거래소, 직접 경쟁 |
| 🟡 | 코빗 | 국내 중형 거래소, 규제 준수 선도 |
| 🟡 | 고팍스 | 국내 거래소, 기관 투자자 특화 |

### Global Players
| 우선순위 | 기업명 | 포함 근거 |
|----------|--------|-----------|
| 🔴 | Binance | 글로벌 1위 거래량, 한국 사용자 다수 |
| 🔴 | Coinbase | 미국 상장 거래소, 기관 신뢰성 벤치마크 |
| 🟡 | OKX | 글로벌 Top 3, 아시아 점유율 높음 |
| 🟡 | Bybit | 파생상품 특화, 빠른 성장 |
| 🟢 | Kraken | 유럽 중심, 규제 준수 모델 참고 |

---

## 2. Player별 상세 분석

각 🔴 핵심 경쟁자와 🟡 주요 관찰 대상에 대해 아래 구조로 작성하세요:

### [기업명]
> Domestic / Global | 🔴 핵심 경쟁자

#### 기본 개요
- 국가:
- 설립:
- 창업자: (학력, 커리어)
- 현 CEO:
- 임직원 수:

#### 규모
- 상장 여부: (상장 거래소, 연도 또는 비상장)
- 시가총액 / 밸류에이션: (기준일, 출처)
- 최근 3개년 매출 추이:
- (비상장 시) 누적 투자액, 최근 라운드, 주요 투자자:

#### 사업 개요
| 사업 영역 | BM | 고객군 | 매출 비중(추정) | 출처 |
|----------|----|--------|--------------|------|

**성과 배경:**
- 차별점:
- KSF 충족 여부: (Step 3 KSF와 연결)
- 주요 성장 요인:

#### 최근 전략 방향성
- 공식 발표 (Earnings call / IR):
- 비공식 신호 (채용·상표·뉴스):
- M&A·파트너십:

#### 최근 이슈
| 날짜 | 유형 | 제목 | 요약 | 경쟁 구도 함의 |
|------|------|------|------|----------------|
| YYYY-MM | 🚨/⚠️/ℹ️/✅ | | | |

---

## 3. 시장 KSF (Key Success Factor)

### Must-Have (합계 ≥ 60점)
| 항목 | 정의 | 가중치 | 필수인 이유 |
|------|------|--------|-------------|

### Good-to-Have (합계 ≤ 40점)
| 항목 | 정의 | 가중치 | 유리한 이유 |
|------|------|--------|-------------|

---

## 4. KSF 기반 Player 평가

| KSF 항목 | 가중치 | 두나무(업비트) | 빗썸 | Binance | Coinbase | OKX |
|----------|--------|--------------|------|---------|----------|-----|
| [Must] 항목 | 점 | 상/중/하 — 근거 | | | | |
| **총점 (정량화)** | **100** | | | | | |

### 평가 해석
- 항목별 선두 Player:
- 두나무 위치 및 주요 Gap:
- 단기 강화 우선순위:
- 중기 강화 우선순위:

---

## 5. 포지셔닝 맵

**X축:** [KSF 항목명]
**Y축:** [KSF 항목명]

| Player | [X축] 수준 | [Y축] 수준 | 포지션 해석 |
|--------|-----------|-----------|------------|
| 두나무(업비트) | | | |
| 빗썸 | | | |
| Binance | | | |
| Coinbase | | | |

**White Space 관찰:** [아무도 없는 포지션과 기회 여부 해석]

---

## 6. 시나리오별 위협 분석

> Feasibility **'상'인 시나리오만** 출력. 최대 3개, '상'이 없으면 "현재 시점에서 Feasibility '상'에 해당하는 시나리오 없음" 표기.

### 시나리오 N — [제목] *(Feasibility: 상)*

**내용:** [어떤 Player가 어떤 행동을 어떤 조건에서 취하는지 2~3줄]

**위협 수준:** 상 / 중 / 하

**위협 수준 근거:** [한 줄]

**우리의 Action Plan**
- 단기 (0~6개월): [구체적 대응 행동]
- 중기 (6~18개월): [전략적 포지션 강화 방향]
"""
        return await self._claude(system, prompt, max_tokens=16000)

    async def validate(self, output, context: AgentContext) -> QualityReport:
        checks = []
        analysis = output.analysis or ""

        has_swot = "SWOT" in analysis or ("강점" in analysis and "약점" in analysis)
        checks.append(QualityCheck(
            criterion="SWOT 분석 포함",
            target="Strengths/Weaknesses/Opportunities/Threats",
            actual="포함" if has_swot else "미포함",
            level=QualityLevel.PASS if has_swot else QualityLevel.FAIL,
        ))

        has_matrix = "매트릭스" in analysis or "|" in analysis
        checks.append(QualityCheck(
            criterion="비교 분석 매트릭스 포함",
            target="표 형식 비교 포함",
            actual="포함" if has_matrix else "미포함",
            level=QualityLevel.PASS if has_matrix else QualityLevel.WARNING,
        ))

        has_positioning = "포지셔닝" in analysis
        checks.append(QualityCheck(
            criterion="포지셔닝 맵 포함",
            target="포함",
            actual="포함" if has_positioning else "미포함",
            level=QualityLevel.PASS if has_positioning else QualityLevel.WARNING,
        ))

        pass_count = sum(1 for c in checks if c.level == QualityLevel.PASS)
        pass_rate = pass_count / len(checks)
        return QualityReport(
            overall=QualityLevel.PASS if pass_rate >= 0.67 else QualityLevel.WARNING,
            checks=checks,
            pass_rate=pass_rate,
            summary=f"{len(checks)}개 항목 중 {pass_count}개 통과",
        )
