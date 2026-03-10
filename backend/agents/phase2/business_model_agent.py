"""
Agent #9: 사업모델/밸류체인 분석 Agent
역할: 밸류체인 분석 및 사업 기회 도출
Phase 2 - 분석 & 심층 리서치
"""
from __future__ import annotations

from typing import Any, Dict

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentContext, AgentPhase, QualityCheck, QualityLevel, QualityReport


class BusinessModelAgent(BaseAgent):
    AGENT_ID   = "p2_bizmodel"
    AGENT_NAME = "사업모델/밸류체인 분석 Agent"
    PHASE      = AgentPhase.PHASE2_ANALYSIS

    ROLE = "밸류체인 분석 및 사업 기회 도출"
    TASKS = [
        "산업별 밸류체인 분석",
        "각 단계별 플레이어/수익모델 매핑",
        "신규 사업 기회 영역 식별",
        "BM 벤치마킹",
    ]
    OUTPUT_TYPES = [
        "밸류체인 맵",
        "수익모델 분석표",
        "사업 기회 매트릭스",
        "BM 벤치마크 리포트 (MD+XLSX)",
    ]
    QUALITY_CRITERIA = [
        "밸류체인 완전성 (누락 영역 0)",
        "수익모델 정량 분석 포함",
        "실현가능성 평가",
        "레퍼런스 충분성",
    ]
    DATA_SOURCES = ["Phase 1-2 전체 결과물", "업계 BM 사례", "투자 심사 자료"]
    API_TOOLS   = ["Phase 1-2 Agent 결과물", "내부 DB", "PitchBook API"]

    async def collect_data(self, context: AgentContext) -> Dict[str, Any]:
        prev = context.previous_results
        data = {
            "topic": context.scope.topic,
            "industries": context.scope.industries,
        }

        # Phase 1, 2 결과 집계
        if "p1_company" in prev:
            data["company_analysis"] = prev["p1_company"].analysis
        if "p2_market" in prev:
            data["market_analysis"] = prev["p2_market"].analysis
        if "p2_competitor" in prev:
            data["competitor_analysis"] = prev["p2_competitor"].analysis

        return data

    async def analyze(self, context: AgentContext, raw_data: Dict[str, Any]) -> str:
        market_analysis = raw_data.get("market_analysis", "")
        competitor_analysis = raw_data.get("competitor_analysis", "")

        system = """당신은 사업 전략 및 비즈니스 모델 전문가입니다.
산업 밸류체인을 분석하고, 각 단계별 수익 기회와 신규 사업 가능성을 평가하세요.
실현 가능성과 당사의 역량을 고려한 현실적인 분석을 제공하세요.
반드시 한국어로 작성하고, Markdown 형식을 사용하세요."""

        prompt = f"""
리서치 주제: {context.scope.topic}
분석 산업: {', '.join(context.scope.industries or ['크립토', 'DeFi', 'fintech'])}

## Phase 2 시장 분석 요약
{(market_analysis or '')[:1500]}

## Phase 2 경쟁사 분석 요약
{(competitor_analysis or '')[:1000]}

위 분석을 바탕으로 밸류체인 분석 및 사업 기회 리포트를 작성하세요:

## 1. 산업 밸류체인 맵

### 크립토/블록체인 밸류체인
각 단계별:
| 단계 | 주요 활동 | 핵심 플레이어 | 수익 구조 | 마진 수준 |
|------|----------|------------|----------|----------|
| 인프라 레이어 | | | | |
| 프로토콜 레이어 | | | | |
| 애플리케이션 레이어 | | | | |
| 사용자 인터페이스 | | | | |
| 결제/정산 | | | | |

## 2. 수익 모델 분석

### 주요 수익 모델 유형
각 BM:
- **모델명**: 설명
- **대표 기업**: 사례
- **수익 규모**: 추정
- **마진 수준**: 높음/중간/낮음
- **확장성**: 높음/중간/낮음

## 3. 신규 사업 기회 매트릭스
| 사업 기회 | 시장 규모 | 실현가능성 | 경쟁 강도 | 당사 역량 적합성 | 우선순위 |
|----------|----------|-----------|----------|----------------|--------|

## 4. 글로벌 BM 벤치마킹 (Top 5 사례)
각 사례:
### [기업명] - [사업 모델명]
- 핵심 메커니즘
- 수익 구조
- 성공 요인
- 당사 적용 가능성

## 5. 사업 기회 심층 평가 (Top 3)
각 기회:
### 기회 [번호]: [기회명]
- **시장 규모 추정**: XXX억원
- **수익 모델**: 설명
- **필요 역량**: 목록
- **진입 장벽**: 높음/중간/낮음
- **예상 ROI**: 추정
- **실행 로드맵**: 단계별 계획

## 6. 밸류체인 내 당사 포지셔닝
- 현재 위치
- 강화할 영역
- 진출 고려 영역
- 파트너십 대상 영역
"""
        return await self._claude(system, prompt, max_tokens=4096)

    async def validate(self, output, context: AgentContext) -> QualityReport:
        checks = []
        analysis = output.analysis or ""

        has_value_chain = "밸류체인" in analysis or "레이어" in analysis
        checks.append(QualityCheck(
            criterion="밸류체인 맵 포함",
            target="단계별 밸류체인 분석",
            actual="포함" if has_value_chain else "미포함",
            level=QualityLevel.PASS if has_value_chain else QualityLevel.FAIL,
        ))

        has_bm = "수익 모델" in analysis or "BM" in analysis
        checks.append(QualityCheck(
            criterion="수익 모델 분석 포함",
            target="포함",
            actual="포함" if has_bm else "미포함",
            level=QualityLevel.PASS if has_bm else QualityLevel.WARNING,
        ))

        has_opportunities = "사업 기회" in analysis or "신규 사업" in analysis
        checks.append(QualityCheck(
            criterion="사업 기회 매트릭스 포함",
            target="포함",
            actual="포함" if has_opportunities else "미포함",
            level=QualityLevel.PASS if has_opportunities else QualityLevel.WARNING,
        ))

        pass_count = sum(1 for c in checks if c.level == QualityLevel.PASS)
        pass_rate = pass_count / len(checks)
        return QualityReport(
            overall=QualityLevel.PASS if pass_rate >= 0.67 else QualityLevel.WARNING,
            checks=checks,
            pass_rate=pass_rate,
            summary=f"{len(checks)}개 항목 중 {pass_count}개 통과",
        )
