"""
Agent #14: 시각화 & 대시보드 Agent
역할: 데이터 시각화 및 대시보드 구축
Phase 4 - 산출물 & 전달

품질 기준:
- 대시보드 로딩 3초 이내
- 데이터 실시간 반영
- UI/UX 직관성
- 모바일 호환성
"""
from __future__ import annotations

from typing import Any, Dict, List

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentContext, AgentPhase, QualityCheck, QualityLevel, QualityReport


class DashboardAgent(BaseAgent):
    AGENT_ID   = "p4_dashboard"
    AGENT_NAME = "시각화 & 대시보드 Agent"
    PHASE      = AgentPhase.PHASE4_OUTPUT

    ROLE = "데이터 시각화 및 대시보드 구축"
    TASKS = [
        "핵심 지표 대시보드 설계/구축",
        "인터랙티브 차트/그래프 생성",
        "실시간 데이터 업데이트 파이프라인",
        "알림/노티피케이션 시스템 구축",
    ]
    OUTPUT_TYPES = [
        "MI 대시보드 (웹 기반)",
        "핵심 지표 모니터링 화면",
        "자동 업데이트 파이프라인",
        "알림 시스템 (Dashboard+XLSX)",
    ]
    QUALITY_CRITERIA = [
        "대시보드 로딩 3초 이내",
        "데이터 실시간 반영",
        "UI/UX 직관성",
        "모바일 호환성",
    ]
    DATA_SOURCES = ["Phase 1-3 전체 결과물", "실시간 API 데이터 피드"]
    API_TOOLS   = ["Tableau/Looker API", "Google Sheets API", "Slack Webhook", "Plotly/D3.js"]

    async def collect_data(self, context: AgentContext) -> Dict[str, Any]:
        prev = context.previous_results

        dashboard_data = {
            "topic": context.scope.topic,
            "metrics": {},
            "charts": [],
            "alerts": [],
        }

        # Phase 1 시장 데이터 추출
        if "p1_industry" in prev:
            raw = prev["p1_industry"].raw_data
            global_data = raw.get("coingecko_global", {})
            markets = raw.get("coingecko_markets", [])[:10]
            protocols = raw.get("defillama_protocols", [])[:10]

            dashboard_data["metrics"]["market"] = {
                "total_market_cap_usd": global_data.get("total_market_cap_usd", 0),
                "total_volume_24h_usd": global_data.get("total_volume_24h_usd", 0),
                "btc_dominance_pct": global_data.get("btc_dominance_pct", 0),
                "market_cap_change_24h_pct": global_data.get("market_cap_change_24h_pct", 0),
            }

            dashboard_data["charts"].append({
                "type": "bar",
                "title": "Top 10 암호화폐 시가총액",
                "data": [
                    {"label": m.get("name", ""), "value": m.get("market_cap_usd", 0) / 1e9, "unit": "B USD"}
                    for m in markets if "error" not in m
                ],
            })

            dashboard_data["charts"].append({
                "type": "bar",
                "title": "DeFi 프로토콜 TVL Top 10",
                "data": [
                    {"label": p.get("name", ""), "value": p.get("tvl_usd", 0) / 1e6, "unit": "M USD"}
                    for p in protocols if "error" not in p
                ],
            })

            # 24h 변화율 차트
            dashboard_data["charts"].append({
                "type": "bar_horizontal",
                "title": "24시간 가격 변동률 (%)",
                "data": [
                    {
                        "label": m.get("name", ""),
                        "value": m.get("price_change_24h_pct", 0),
                        "color": "green" if m.get("price_change_24h_pct", 0) >= 0 else "red",
                    }
                    for m in markets if "error" not in m
                ],
            })

        # Phase 3 인사이트에서 알림 생성
        if "p3_insight" in prev:
            dashboard_data["alerts"].append({
                "type": "info",
                "message": "MI 분석 완료: " + prev["p3_insight"].summary[:100],
            })

        if "p1_regulatory" in prev:
            reg_summary = prev["p1_regulatory"].summary
            if "High" in reg_summary or "즉시" in reg_summary:
                dashboard_data["alerts"].append({
                    "type": "warning",
                    "message": "규제 주의: " + reg_summary[:100],
                })

        # 에이전트 성과 요약
        dashboard_data["metrics"]["session"] = {
            "total_agents": len(prev),
            "completed": sum(1 for o in prev.values() if o.status.value == "completed"),
            "total_data_points": sum(o.data_points_collected for o in prev.values()),
            "agents_quality": {
                a_id: o.quality.overall.value if o.quality else "unknown"
                for a_id, o in prev.items()
            },
        }

        return dashboard_data

    async def analyze(self, context: AgentContext, raw_data: Dict[str, Any]) -> str:
        metrics = raw_data.get("metrics", {})
        charts = raw_data.get("charts", [])
        alerts = raw_data.get("alerts", [])

        market_metrics = metrics.get("market", {})
        session_metrics = metrics.get("session", {})

        system = """당신은 데이터 시각화 전문가입니다.
수집된 데이터를 기반으로 대시보드 설계 및 주요 시각화 인사이트를 제공하세요.
각 차트가 전달해야 할 핵심 메시지를 명확히 하세요.
반드시 한국어로 작성하고, Markdown 형식을 사용하세요."""

        charts_summary = "\n".join([
            f"- {c['title']}: {len(c.get('data', []))}개 데이터 포인트"
            for c in charts
        ])

        prompt = f"""
리서치 주제: {context.scope.topic}

## 핵심 지표 현황
- 글로벌 암호화폐 시가총액: ${market_metrics.get('total_market_cap_usd', 0)/1e9:.0f}B
- 24시간 거래량: ${market_metrics.get('total_volume_24h_usd', 0)/1e9:.0f}B
- BTC 도미넌스: {market_metrics.get('btc_dominance_pct', 0):.1f}%
- 시총 24h 변화: {market_metrics.get('market_cap_change_24h_pct', 0):+.1f}%

## 분석 세션 현황
- 완료된 에이전트: {session_metrics.get('completed', 0)}/{session_metrics.get('total_agents', 0)}
- 수집된 데이터 포인트: {session_metrics.get('total_data_points', 0):,}개

## 생성된 차트 목록
{charts_summary}

## 알림 현황
{chr(10).join([f"- [{a['type'].upper()}] {a['message']}" for a in alerts])}

대시보드 설계 및 시각화 인사이트 리포트를 작성하세요:

## 1. 대시보드 설계 개요
- 핵심 KPI 위젯 구성
- 레이아웃 설계 (어떤 차트를 어디에 배치)
- 업데이트 주기

## 2. 차트별 핵심 인사이트
각 차트가 전달하는 핵심 메시지와 해석 가이드

## 3. 알림/모니터링 기준
- 어떤 조건에서 알림을 발송할지
- 알림 임계값 설정 기준

## 4. 데이터 갱신 전략
- 실시간 갱신이 필요한 지표
- 일 1회 갱신으로 충분한 지표
- 주간 갱신 지표

## 5. 모바일 최적화 방안
- 모바일에서 우선 표시할 핵심 위젯
- 터치 친화적 인터랙션 설계

## 6. 차트 해석 가이드
각 주요 차트에 대한 해석 방법과 주의사항
"""
        return await self._claude(system, prompt, max_tokens=2000)

    def get_dashboard_config(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """프론트엔드에서 바로 사용 가능한 대시보드 설정 반환"""
        return {
            "metrics": raw_data.get("metrics", {}),
            "charts": raw_data.get("charts", []),
            "alerts": raw_data.get("alerts", []),
        }

    async def validate(self, output, context: AgentContext) -> QualityReport:
        checks = []

        charts_count = len(output.raw_data.get("charts", []))
        checks.append(QualityCheck(
            criterion="차트 생성 수",
            target="3개 이상",
            actual=f"{charts_count}개",
            level=QualityLevel.PASS if charts_count >= 3 else QualityLevel.WARNING,
        ))

        has_metrics = bool(output.raw_data.get("metrics", {}).get("market"))
        checks.append(QualityCheck(
            criterion="핵심 지표 수집",
            target="시장 지표 포함",
            actual="포함" if has_metrics else "미포함",
            level=QualityLevel.PASS if has_metrics else QualityLevel.WARNING,
        ))

        has_alerts = "알림" in (output.analysis or "")
        checks.append(QualityCheck(
            criterion="알림 기준 설정",
            target="포함",
            actual="포함" if has_alerts else "미포함",
            level=QualityLevel.PASS if has_alerts else QualityLevel.WARNING,
        ))

        pass_count = sum(1 for c in checks if c.level == QualityLevel.PASS)
        pass_rate = pass_count / len(checks)
        return QualityReport(
            overall=QualityLevel.PASS if pass_rate >= 0.67 else QualityLevel.WARNING,
            checks=checks,
            pass_rate=pass_rate,
            summary=f"{len(checks)}개 항목 중 {pass_count}개 통과",
        )
