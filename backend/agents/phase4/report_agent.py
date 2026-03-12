"""
Agent #13: 리포트 생성 Agent
역할: 최종 MI 리포트 작성
Phase 4 - 산출물 & 전달

품질 기준:
- 경영진 가독성
- 데이터 시각화 품질
- 논리적 스토리라인
- 오탈자/포맷 오류 0건
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentContext, AgentPhase, QualityCheck, QualityLevel, QualityReport


class ReportAgent(BaseAgent):
    AGENT_ID   = "p4_report"
    AGENT_NAME = "리포트 생성 Agent"
    PHASE      = AgentPhase.PHASE4_OUTPUT

    ROLE = "최종 MI 리포트 작성"
    TASKS = [
        "경영진용 Executive Summary 작성",
        "상세 분석 리포트 작성 (산업별/주제별)",
        "부록/참고자료 정리",
        "리포트 포맷팅 및 디자인",
    ]
    OUTPUT_TYPES = [
        "Executive Summary (1-2p)",
        "상세 MI 리포트 (20-30p)",
        "부록 데이터북",
        "프레젠테이션 자료 (PPTX+PDF)",
    ]
    QUALITY_CRITERIA = [
        "경영진 가독성",
        "데이터 시각화 품질",
        "논리적 스토리라인",
        "오탈자/포맷 오류 0건",
    ]
    DATA_SOURCES = ["Phase 1-3 전체 검증 완료 결과물"]
    API_TOOLS   = ["Claude API (문서 생성)", "Google Docs API", "PPTX 생성 라이브러리"]

    async def collect_data(self, context: AgentContext) -> Dict[str, Any]:
        prev = context.previous_results

        report_data = {
            "topic": context.scope.topic,
            "generated_at": datetime.utcnow().isoformat(),
            "scope": context.scope.model_dump(),
            "agent_summaries": {},
            "key_analyses": {},
        }

        for agent_id, output in prev.items():
            report_data["agent_summaries"][agent_id] = {
                "name": output.agent_name,
                "phase": output.phase.value,
                "summary": output.summary,
                "status": output.status.value,
                "quality": output.quality.overall.value if output.quality else "unknown",
            }
            if output.analysis:
                report_data["key_analyses"][agent_id] = output.analysis[:3000]

        return report_data

    async def analyze(self, context: AgentContext, raw_data: Dict[str, Any]) -> str:
        summaries = raw_data.get("agent_summaries", {})
        analyses = raw_data.get("key_analyses", {})

        # 중요 분석 결과 추출
        insight_analysis = analyses.get("p3_insight", "")
        strategy_analysis = analyses.get("p3_strategy", "")
        market_analysis = analyses.get("p2_market", "")
        competitor_analysis = analyses.get("p2_competitor", "")
        news_analysis = analyses.get("p1_news", "")
        regulatory_analysis = analyses.get("p1_regulatory", "")
        tech_analysis = analyses.get("p2_tech", "")
        bizmodel_analysis = analyses.get("p2_bizmodel", "")

        # 전체 요약
        all_summaries = "\n".join([
            f"- **{v['name']}** [{v['quality']}]: {v['summary']}"
            for v in summaries.values()
        ])

        system = """당신은 전문 Market Intelligence 리포트 작가입니다.
McKinsey/BCG 수준의 시장 조사 리포트를 작성하세요.
핵심 원칙:
- 모든 섹션에 구체적인 수치(시가총액, 성장률, 점유율, 투자금액 등)를 반드시 포함하세요
- 각 핵심 주장 아래에 데이터 표를 제시하세요
- 인사이트는 인용구(" ") 형식으로 강조하세요
- 각 데이터에 출처를 명시하세요 (예: 1) 출처명, 2) 출처명)
- 비교 분석은 반드시 표 형식을 사용하세요
- 시계열 트렌드를 연도별로 제시하세요
- 결론이 먼저 (Pyramid Principle), 근거는 그 다음에
반드시 한국어로 작성하고, Markdown 형식을 사용하세요."""

        prompt = f"""
리서치 주제: {context.scope.topic}
리포트 생성일: {raw_data.get('generated_at', '')}
분석 기간: 최근 {context.scope.date_range_days}일

## 전체 에이전트 실행 요약
{all_summaries}

## 핵심 인사이트 (Insight Agent 전체 분석)
{insight_analysis[:4000]}

## 전략 시사점 (Strategy Agent 전체 분석)
{strategy_analysis[:4000]}

## 시장 분석 (Market Analysis Agent)
{market_analysis[:2500]}

## 경쟁 분석 (Competitor Agent)
{competitor_analysis[:2500]}

## 뉴스 & 미디어 분석 (News Agent)
{news_analysis[:1500]}

## 규제 환경 분석 (Regulatory Agent)
{regulatory_analysis[:1500]}

## 기술 트렌드 분석 (Tech Agent)
{tech_analysis[:1500]}

## 사업 기회 분석 (BizModel Agent)
{bizmodel_analysis[:1500]}

위 내용을 바탕으로 다음 형식의 최종 MI 리포트를 작성하세요.
**수치 없는 주장, 출처 없는 데이터는 작성하지 마세요.**

---

# Market Intelligence Report
## {context.scope.topic}

**작성일**: {datetime.utcnow().strftime('%Y년 %m월 %d일')}
**분석 기간**: 최근 {context.scope.date_range_days}일
**분석 방법론**: 14개 전문 AI 에이전트 멀티스테이지 분석
**대외비**

---

## Executive Summary

### 핵심 결론 (Key Findings)
> **"** (시장에 대한 가장 중요한 결론 1문장, 수치 포함) **"**

| # | 핵심 발견 | 수치 근거 | 시사점 |
|---|---------|---------|------|
| 1 | | | |
| 2 | | | |
| 3 | | | |

### 즉각 필요 액션
- **오늘 결정**: (무엇을, 왜)
- **이번 달 착수**: (무엇을, 기대효과)
- **분기 내 완료**: (무엇을, 목표 지표)

### 최대 기회 vs 최대 위험
| 구분 | 내용 | 예상 규모 | 대응 기한 |
|------|------|---------|---------|
| 최대 기회 | | $XB | |
| 최대 위험 | | | |

---

## 1. 시장 현황 분석

### 1.1 글로벌 시장 규모 및 성장 추이
> **"** (시장 트렌드 핵심 인사이트) **"**

| 연도 | 시장 규모 | YoY 성장 | 핵심 이벤트 |
|------|---------|---------|----------|
| 2021 | | | |
| 2022 | | | |
| 2023 | | | |
| 2024 | | | |
| 2025E | | | |

### 1.2 시장 세그먼트 현황
| 세그먼트 | 규모 | 비중 | YoY | 주요 플레이어 |
|---------|------|------|-----|------------|

### 1.3 지역별 시장 현황
| 지역 | 규모 | 비중 | 규제 환경 | 진입 기회 |
|------|------|------|---------|---------|

---

## 2. 경쟁 구도 분석

### 2.1 주요 플레이어 현황
> **"** (경쟁 구도 핵심 인사이트) **"**

| 기업 | 국가 | 밸류에이션 | 점유율(추정) | 최근 동향 |
|------|------|---------|-----------|---------|

### 2.2 Value Chain 분석
| 영역 | 주요 플레이어 | 수익 모델 | 성장률 |
|------|-----------|---------|------|

### 2.3 경쟁 강도 평가 (Porter's 5 Forces)
| 요소 | 강도 | 근거 |
|------|------|------|
| 기존 경쟁자 위협 | 상/중/하 | |
| 신규 진입자 위협 | | |
| 대체재 위협 | | |
| 공급자 교섭력 | | |
| 구매자 교섭력 | | |

---

## 3. 규제 & 기술 환경

### 3.1 국가별 규제 현황
| 국가 | 규제명 | 시행일 | 주요 내용 | 당사 영향 |
|------|--------|--------|---------|---------|

### 3.2 핵심 기술 트렌드
| 기술 | 성숙도 | 시장 영향 | 타임라인 |
|------|--------|---------|--------|

---

## 4. 사업 기회 평가

### 4.1 기회 우선순위 매트릭스
| 기회 영역 | 시장 규모 | 성장률 | 실현가능성 | 전략 적합도 | 우선순위 |
|---------|---------|------|---------|-----------|--------|

### 4.2 사업 모델 분석
> **"** (사업 기회에 관한 핵심 인사이트) **"**

| 모델 | 수익 구조 | 예상 수익성 | 필요 역량 | 진입 난이도 |
|------|---------|-----------|---------|---------|

---

## 5. 전략적 권고 및 실행 로드맵

### 5.1 전략 권고 요약
| 기간 | 핵심 과제 | 목표 지표 | 필요 투자 |
|------|---------|---------|---------|
| 단기 (0~3개월) | | | |
| 중기 (3~12개월) | | | |
| 장기 (1~3년) | | | |

### 5.2 리스크 관리
| 리스크 | 발생확률 | 영향도 | 대응 방안 | 기한 |
|--------|---------|--------|---------|-----|

---

## 6. 부록

### A. 데이터 출처
### B. 분석 방법론 및 한계
### C. 주요 용어 정의

---
*본 리포트는 14개 AI 에이전트가 수집/분석한 데이터를 기반으로 작성되었습니다.*
*최종 의사결정 시 전문가 검토를 권장합니다.*
"""
        return await self._claude(system, prompt, max_tokens=16000)

    async def validate(self, output, context: AgentContext) -> QualityReport:
        checks = []
        analysis = output.analysis or ""

        has_exec_summary = "Executive Summary" in analysis or "핵심 발견" in analysis
        checks.append(QualityCheck(
            criterion="Executive Summary 포함",
            target="경영진용 요약 포함",
            actual="포함" if has_exec_summary else "미포함",
            level=QualityLevel.PASS if has_exec_summary else QualityLevel.FAIL,
        ))

        report_length = len(analysis)
        checks.append(QualityCheck(
            criterion="리포트 분량",
            target="3000자 이상",
            actual=f"{report_length}자",
            level=QualityLevel.PASS if report_length >= 3000 else QualityLevel.WARNING,
        ))

        has_action = "액션" in analysis or "실행" in analysis or "권고" in analysis
        checks.append(QualityCheck(
            criterion="실행 가능한 권고 포함",
            target="포함",
            actual="포함" if has_action else "미포함",
            level=QualityLevel.PASS if has_action else QualityLevel.WARNING,
        ))

        pass_count = sum(1 for c in checks if c.level == QualityLevel.PASS)
        pass_rate = pass_count / len(checks)
        return QualityReport(
            overall=QualityLevel.PASS if pass_rate >= 0.67 else QualityLevel.WARNING,
            checks=checks,
            pass_rate=pass_rate,
            summary=f"{len(checks)}개 항목 중 {pass_count}개 통과",
        )
