"""
Agent #12: 품질 검증 (QA) Agent
역할: 전체 산출물 수치적 품질 검증 및 팩트 체크
Phase 3 - 종합 & 인사이트

수치적 품질 기준 (모두 충족해야 Phase 4 진행):
- 데이터 포인트 수: 총 50개 이상
- 에이전트 통과율: Phase 1-3 에이전트 중 80% 이상 PASS/WARNING
- 분석 텍스트 길이: 각 에이전트 분석 평균 500자 이상
- 출처 다양성: 총 고유 출처 10개 이상
- 정량 데이터 포함률: 에이전트 중 70% 이상에 수치 포함
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import (
    AgentContext,
    AgentPhase,
    QualityCheck,
    QualityLevel,
    QualityReport,
)


# ─── 수치적 품질 임계값 ───────────────────────────────────────────
QA_THRESHOLDS = {
    "min_data_points_total":    50,    # 전체 데이터 포인트 합계
    "min_agent_pass_rate":      0.80,  # Phase 1~3 에이전트 중 PASS+WARNING 비율
    "min_avg_analysis_length":  500,   # 에이전트 분석 평균 글자 수
    "min_unique_sources":       10,    # 중복 제거한 출처 수
    "min_quantitative_rate":    0.70,  # 수치(숫자) 포함 에이전트 비율
    "min_insight_count":        3,     # Insight/Strategy 에이전트 인사이트 항목 수
    "overall_pass_threshold":   0.75,  # 전체 QA 통과율 (이 이상이어야 Phase 4 진행)
}

_NUMBER_PATTERN = re.compile(r'\d[\d,\.]*\s*(%|억|조|만|B|M|K|USD|KRW|원|달러)')


class QAAgent(BaseAgent):
    AGENT_ID   = "p3_qa"
    AGENT_NAME = "품질 검증 (QA) Agent"
    PHASE      = AgentPhase.PHASE3_SYNTHESIS

    ROLE = "전체 산출물 수치적 품질 검증 및 팩트 체크"
    TASKS = [
        "데이터 포인트 수량 계수 및 임계값 검증",
        "에이전트별 분석 깊이(글자 수) 측정",
        "출처 다양성 및 신뢰도 평가",
        "정량 데이터 포함률 측정",
        "논리적 일관성 및 내부 모순 검토",
        "편향성 검토 및 보완 제안",
    ]
    OUTPUT_TYPES = [
        "수치적 QA 스코어카드",
        "에이전트별 품질 지표 테이블",
        "재실행 요구 사항 목록 (기준 미충족 항목)",
        "Phase 4 진행 가부 판정 (PASS/RETRY)",
    ]
    QUALITY_CRITERIA = [
        f"전체 데이터 포인트 {QA_THRESHOLDS['min_data_points_total']}개 이상",
        f"에이전트 통과율 {QA_THRESHOLDS['min_agent_pass_rate']*100:.0f}% 이상",
        f"평균 분석 길이 {QA_THRESHOLDS['min_avg_analysis_length']}자 이상",
        f"고유 출처 {QA_THRESHOLDS['min_unique_sources']}개 이상",
        f"정량 데이터 포함 에이전트 {QA_THRESHOLDS['min_quantitative_rate']*100:.0f}% 이상",
    ]
    DATA_SOURCES = ["Phase 1-3 전체 산출물", "원본 데이터 소스"]
    API_TOOLS   = ["내부 산출물 교차 검증"]

    # 품질 미달 시 재실행 대상 Phase 계산
    def get_retry_phases(self, score: "QAScore") -> List[int]:
        """수치 기준 미충족 항목에 따라 재실행이 필요한 Phase 목록 반환"""
        retry = set()
        if not score.data_points_ok:
            retry.update([1, 2])   # 데이터 부족 → Phase 1,2 재실행
        if not score.agent_pass_rate_ok:
            retry.update([1, 2])
        if not score.avg_length_ok:
            retry.update([2, 3])   # 분석 깊이 부족 → Phase 2,3 재실행
        if not score.sources_ok:
            retry.add(1)           # 출처 부족 → Phase 1 재실행
        if not score.quantitative_rate_ok:
            retry.update([1, 2])
        return sorted(retry)

    async def collect_data(self, context: AgentContext) -> Dict[str, Any]:
        prev = context.previous_results

        all_analyses = {}
        all_sources: List[str] = []

        for agent_id, output in prev.items():
            analysis_text = output.analysis or ""
            has_numbers = bool(_NUMBER_PATTERN.search(analysis_text))

            all_analyses[agent_id] = {
                "name": output.agent_name,
                "phase": output.phase.value,
                "summary": output.summary,
                "analysis_length": len(analysis_text),
                "analysis_excerpt": analysis_text[:600],
                "quality_level": output.quality.overall.value if output.quality else "unknown",
                "quality_pass_rate": output.quality.pass_rate if output.quality else 0.0,
                "sources": output.sources_used,
                "data_points": output.data_points_collected,
                "warnings": output.warnings,
                "status": output.status.value,
                "has_quantitative_data": has_numbers,
            }
            all_sources.extend(output.sources_used)

        # 집계 수치
        total_data_points = sum(v["data_points"] for v in all_analyses.values())
        unique_sources = len(set(all_sources))
        non_qa_agents = {k: v for k, v in all_analyses.items() if k != "p3_qa"}
        agent_count = len(non_qa_agents)
        pass_agents = sum(
            1 for v in non_qa_agents.values()
            if v["quality_level"] in ("pass", "warning")
        )
        agent_pass_rate = pass_agents / agent_count if agent_count > 0 else 0.0
        analysis_lengths = [v["analysis_length"] for v in non_qa_agents.values() if v["analysis_length"] > 0]
        avg_length = sum(analysis_lengths) / len(analysis_lengths) if analysis_lengths else 0
        quant_count = sum(1 for v in non_qa_agents.values() if v["has_quantitative_data"])
        quant_rate = quant_count / agent_count if agent_count > 0 else 0.0

        return {
            "all_analyses": all_analyses,
            "total_agents": len(all_analyses),
            "metrics": {
                "total_data_points": total_data_points,
                "unique_sources": unique_sources,
                "agent_pass_rate": agent_pass_rate,
                "pass_agents": pass_agents,
                "total_agents_checked": agent_count,
                "avg_analysis_length": avg_length,
                "quantitative_rate": quant_rate,
                "quant_agents": quant_count,
            },
        }

    async def analyze(self, context: AgentContext, raw_data: Dict[str, Any]) -> str:
        m = raw_data.get("metrics", {})
        all_analyses = raw_data.get("all_analyses", {})
        t = QA_THRESHOLDS

        # 각 임계값 통과 여부
        dp_ok    = m.get("total_data_points", 0) >= t["min_data_points_total"]
        rate_ok  = m.get("agent_pass_rate", 0)  >= t["min_agent_pass_rate"]
        len_ok   = m.get("avg_analysis_length", 0) >= t["min_avg_analysis_length"]
        src_ok   = m.get("unique_sources", 0)    >= t["min_unique_sources"]
        qnt_ok   = m.get("quantitative_rate", 0) >= t["min_quantitative_rate"]

        checks_passed = sum([dp_ok, rate_ok, len_ok, src_ok, qnt_ok])
        overall_score = checks_passed / 5
        phase4_ok = overall_score >= t["overall_pass_threshold"]

        # 에이전트별 품질 테이블 구성
        agent_table = "\n".join([
            f"| {v['name']} | {v['data_points']} | {v['analysis_length']:,}자 | "
            f"{'O' if v['has_quantitative_data'] else 'X'} | {v['quality_level']} |"
            for v in all_analyses.values()
        ])

        quality_summary = "\n".join([
            f"- {v['name']}: {v['quality_level']} (분석 {v['analysis_length']:,}자, 데이터 {v['data_points']}점)"
            for v in all_analyses.values()
        ])

        system = """당신은 Market Intelligence 수치적 품질 검증 전문가입니다.
정량 지표를 기반으로 분석 품질을 엄격하게 평가하고, 구체적인 수치와 함께 판정하세요.
반드시 한국어로 작성하고, Markdown 형식을 사용하세요."""

        prompt = f"""
리서치 주제: {context.scope.topic}
검토 에이전트: {raw_data.get('total_agents', 0)}개

## 수치적 품질 지표 측정 결과

| 지표 | 측정값 | 기준값 | 판정 |
|------|--------|--------|------|
| 전체 데이터 포인트 수 | {m.get('total_data_points', 0)}개 | ≥{t['min_data_points_total']}개 | {'✅ PASS' if dp_ok else '❌ FAIL'} |
| 에이전트 통과율 | {m.get('agent_pass_rate', 0)*100:.1f}% ({m.get('pass_agents',0)}/{m.get('total_agents_checked',0)}) | ≥{t['min_agent_pass_rate']*100:.0f}% | {'✅ PASS' if rate_ok else '❌ FAIL'} |
| 평균 분석 길이 | {m.get('avg_analysis_length', 0):,.0f}자 | ≥{t['min_avg_analysis_length']:,}자 | {'✅ PASS' if len_ok else '❌ FAIL'} |
| 고유 출처 수 | {m.get('unique_sources', 0)}개 | ≥{t['min_unique_sources']}개 | {'✅ PASS' if src_ok else '❌ FAIL'} |
| 정량 데이터 포함률 | {m.get('quantitative_rate', 0)*100:.1f}% ({m.get('quant_agents',0)}개 에이전트) | ≥{t['min_quantitative_rate']*100:.0f}% | {'✅ PASS' if qnt_ok else '❌ FAIL'} |

**종합 QA 점수: {checks_passed}/5 ({overall_score*100:.0f}%) → {'✅ Phase 4 진행' if phase4_ok else '⚠️ 재실행 필요'}**

## 에이전트별 품질 현황
{quality_summary}

## 에이전트별 상세 지표
| 에이전트 | 데이터포인트 | 분석길이 | 정량데이터 | 품질등급 |
|---------|------------|--------|----------|--------|
{agent_table}

위 측정 결과를 바탕으로 종합 QA 리포트를 작성하세요:

## 1. 수치적 QA 스코어카드 요약
- 측정 항목별 점수 및 판정 결과 설명
- 전체 신뢰도 점수: /100

## 2. 에이전트별 품질 상세 평가
- 각 에이전트의 강점과 보완 필요 사항
- 특히 FAIL 에이전트의 구체적 문제점 지적

## 3. 팩트 체크 및 논리 일관성
- 에이전트 간 모순되거나 충돌하는 주장 목록
- 데이터와 결론의 불일치 사항
- 수치 검증 필요 항목

## 4. 편향성 분석
- 지역 편향: 특정 국가/지역 과대/과소 대표 여부
- 시간 편향: 특정 기간 치우침 여부
- 확증 편향: 기존 가정만 강화하는 분석 여부
- 보완 방안

## 5. {'재실행 불필요 - Phase 4 진행 승인' if phase4_ok else '재실행 필요 항목 및 대상 Phase'}
{'Phase 4 (리포트/대시보드 생성) 진행을 승인합니다. 주요 유보 사항만 기술.' if phase4_ok else '''
다음 기준 미충족으로 일부 Phase 재실행을 권고합니다:
- 미충족 항목별 재실행 대상 Phase 명시
- 재실행 시 특히 보강해야 할 데이터/분석 항목
- 예상 개선 효과
'''}

## 6. 최종 판정
- **QA 점수**: {checks_passed}/5 ({overall_score*100:.0f}%)
- **Phase 4 진행 여부**: {'APPROVED ✅' if phase4_ok else 'RETRY REQUIRED ⚠️'}
- **유효 기간 권고**: 이 리포트 데이터의 신선도 기준
"""
        analysis = await self._claude(system, prompt, max_tokens=4000)

        # 구조화된 판정 데이터를 analysis에 첨부
        verdict = "PASS" if phase4_ok else "RETRY"
        analysis += f"\n\n<!-- QA_VERDICT:{verdict} QA_SCORE:{overall_score:.3f} -->"
        return analysis

    async def validate(self, output, context: AgentContext) -> QualityReport:
        checks = []
        m = output.raw_data.get("metrics", {})
        t = QA_THRESHOLDS

        def _check(criterion: str, target: str, actual_val, threshold, unit: str = "") -> QualityCheck:
            ok = actual_val >= threshold
            return QualityCheck(
                criterion=criterion,
                target=f"≥{threshold}{unit}",
                actual=f"{actual_val}{unit}",
                level=QualityLevel.PASS if ok else QualityLevel.FAIL,
                note=None,
            )

        checks.append(_check(
            "전체 데이터 포인트",
            f"≥{t['min_data_points_total']}개",
            m.get("total_data_points", 0),
            t["min_data_points_total"],
            "개",
        ))
        checks.append(_check(
            "에이전트 통과율",
            f"≥{t['min_agent_pass_rate']*100:.0f}%",
            round(m.get("agent_pass_rate", 0) * 100, 1),
            t["min_agent_pass_rate"] * 100,
            "%",
        ))
        checks.append(_check(
            "평균 분석 길이",
            f"≥{t['min_avg_analysis_length']}자",
            round(m.get("avg_analysis_length", 0)),
            t["min_avg_analysis_length"],
            "자",
        ))
        checks.append(_check(
            "고유 출처 수",
            f"≥{t['min_unique_sources']}개",
            m.get("unique_sources", 0),
            t["min_unique_sources"],
            "개",
        ))
        checks.append(_check(
            "정량 데이터 포함률",
            f"≥{t['min_quantitative_rate']*100:.0f}%",
            round(m.get("quantitative_rate", 0) * 100, 1),
            t["min_quantitative_rate"] * 100,
            "%",
        ))

        pass_count = sum(1 for c in checks if c.level == QualityLevel.PASS)
        pass_rate = pass_count / len(checks)
        overall = QualityLevel.PASS if pass_rate >= t["overall_pass_threshold"] else QualityLevel.FAIL

        return QualityReport(
            overall=overall,
            checks=checks,
            pass_rate=pass_rate,
            summary=f"QA {pass_count}/{len(checks)} 통과 ({pass_rate*100:.0f}%) → {'Phase 4 진행' if overall == QualityLevel.PASS else '재실행 필요'}",
        )

    def get_phase4_verdict(self, output) -> Tuple[bool, float]:
        """Phase 4 진행 여부와 QA 점수 반환"""
        if output.quality:
            return (
                output.quality.overall == QualityLevel.PASS,
                output.quality.pass_rate,
            )
        return (False, 0.0)


# QA 점수 데이터 클래스 (get_retry_phases에서 사용)
class QAScore:
    def __init__(self, metrics: Dict[str, Any]):
        t = QA_THRESHOLDS
        self.data_points_ok      = metrics.get("total_data_points", 0) >= t["min_data_points_total"]
        self.agent_pass_rate_ok  = metrics.get("agent_pass_rate", 0)  >= t["min_agent_pass_rate"]
        self.avg_length_ok       = metrics.get("avg_analysis_length", 0) >= t["min_avg_analysis_length"]
        self.sources_ok          = metrics.get("unique_sources", 0)   >= t["min_unique_sources"]
        self.quantitative_rate_ok = metrics.get("quantitative_rate", 0) >= t["min_quantitative_rate"]
