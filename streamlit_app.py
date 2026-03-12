"""
Market Intelligence AI — Streamlit Cloud 배포용
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime

import streamlit as st

st.set_page_config(
    page_title="Market Intelligence AI",
    page_icon="📊",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
html, body, [class*="css"] { font-family: 'Pretendard', -apple-system, sans-serif !important; }
.stApp { background: #F7F8FA; }
.agent-row { padding: 6px 14px; border-radius: 8px; margin: 3px 0; font-size: 14px; }
.agent-running { background: #EEF2FF; border-left: 3px solid #1B3BFF; }
.agent-done    { background: #F0FDF4; border-left: 3px solid #0ABF76; }
.agent-pending { background: #F1F5F9; border-left: 3px solid #CBD5E1; color: #94A3B8; }
.agent-error   { background: #FFF1F2; border-left: 3px solid #F04452; }
.watermark { position: fixed; bottom: 16px; right: 20px; font-size: 11px; color: #9CA3AF; pointer-events: none; }
</style>
<div class="watermark">DUNAMU 경영혁신실 · Confidential</div>
""", unsafe_allow_html=True)


# ── 비밀번호 확인 ──────────────────────────────────────────────────
def check_password() -> bool:
    if st.session_state.get("authenticated"):
        return True

    st.markdown("## 📊 Market Intelligence AI")
    st.markdown("두나무 경영혁신실 내부 시스템입니다.")
    st.divider()

    col1, col2 = st.columns([3, 1])
    with col1:
        pwd = st.text_input("비밀번호", type="password", placeholder="비밀번호 입력",
                            label_visibility="collapsed")
    with col2:
        enter = st.button("입장", use_container_width=True, type="primary")

    if enter or pwd:
        correct = st.secrets.get("PASSWORD", os.getenv("MI_PASSWORD", ""))
        if pwd == correct:
            st.session_state["authenticated"] = True
            st.rerun()
        elif pwd:
            st.error("비밀번호가 틀렸습니다.")
    return False


if not check_password():
    st.stop()


# ── API 키 ──────────────────────────────────────────────────────────
api_key = st.secrets.get("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY", ""))
if not api_key:
    st.error("ANTHROPIC_API_KEY가 설정되지 않았습니다. Streamlit Cloud → Settings → Secrets에 추가하세요.")
    st.stop()
os.environ["ANTHROPIC_API_KEY"] = api_key


# ── 메인 UI ────────────────────────────────────────────────────────
st.markdown("# 📊 Market Intelligence AI")
st.caption("두나무 경영혁신실 · 14개 AI 에이전트 멀티스테이지 분석 플랫폼")
st.divider()

AGENT_ORDER = [
    ("p1_pmo",       "PMO Agent",              1),
    ("p1_news",      "뉴스 & 미디어 모니터링",    1),
    ("p1_industry",  "산업 데이터 수집",          1),
    ("p1_regulatory","규제/정책 동향",            1),
    ("p1_company",   "기업/스타트업 정보",         1),
    ("p2_market",    "시장/산업 분석",            2),
    ("p2_competitor","경쟁사/동종업계 분석",       2),
    ("p2_tech",      "기술 트렌드 분석",          2),
    ("p2_bizmodel",  "사업모델/밸류체인 분석",     2),
    ("p3_insight",   "인사이트 종합",             3),
    ("p3_strategy",  "전략 시사점",              3),
    ("p3_qa",        "품질 검증 (QA)",           3),
    ("p4_report",    "리포트 생성",              4),
    ("p4_dashboard", "시각화 & 대시보드",         4),
]

# ── 입력 폼 ─────────────────────────────────────────────────────────
with st.form("analysis_form"):
    topic = st.text_input("리서치 주제 *",
        placeholder="예: 국내 스테이블코인 시장 동향, 글로벌 가상자산 거래소 경쟁 구도")

    col1, col2 = st.columns(2)
    with col1:
        companies_input = st.text_input("분석 대상 기업 (쉼표 구분, 선택)",
            placeholder="Coinbase, Binance, 빗썸, 두나무")
    with col2:
        date_range = st.selectbox("분석 기간", [7, 30, 60, 90], index=2,
            format_func=lambda x: f"최근 {x}일")

    industries_input = st.text_input("산업 키워드 (쉼표 구분, 선택)",
        placeholder="crypto, fintech, AI, blockchain")

    submitted = st.form_submit_button("🚀 MI 분석 시작", use_container_width=True, type="primary")

# ── 분석 전 에이전트 소개 ────────────────────────────────────────────
if not submitted or not topic:
    st.markdown("### 14개 분석 에이전트 구성")
    cols = st.columns(4)
    phases = {
        "🔵 Phase 1 · 데이터 수집": [a[1] for a in AGENT_ORDER if a[2] == 1],
        "🟣 Phase 2 · 심층 분석":   [a[1] for a in AGENT_ORDER if a[2] == 2],
        "🟢 Phase 3 · 종합":        [a[1] for a in AGENT_ORDER if a[2] == 3],
        "🟡 Phase 4 · 산출물":      [a[1] for a in AGENT_ORDER if a[2] == 4],
    }
    for i, (phase, agents) in enumerate(phases.items()):
        with cols[i]:
            st.markdown(f"**{phase}**")
            for a in agents:
                st.markdown(f"<div class='agent-row agent-pending'>● {a}</div>",
                            unsafe_allow_html=True)
    st.stop()


# ── 분석 실행 ────────────────────────────────────────────────────────
target_companies = [c.strip() for c in companies_input.split(",") if c.strip()]
industries = [i.strip() for i in industries_input.split(",") if i.strip()] or \
             ["crypto", "fintech", "AI"]

st.markdown(f"## 분석 중: **{topic}**")
st.caption(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · 최근 {date_range}일")

progress_bar   = st.progress(0, text="준비 중...")
agent_panel    = st.empty()
log_expander   = st.expander("실시간 로그", expanded=True)
log_placeholder = log_expander.empty()

agent_states: dict[str, str] = {}
log_lines: list[str] = []


def render_agents():
    rows = []
    for aid, aname, phase in AGENT_ORDER:
        state = agent_states.get(aid, "pending")
        css  = {"pending": "agent-pending", "running": "agent-running",
                "done": "agent-done", "error": "agent-error"}.get(state, "agent-pending")
        icon = {"pending": "○", "running": "◌", "done": "✓", "error": "✗"}.get(state, "○")
        rows.append(
            f"<div class='agent-row {css}'>{icon} <b>Phase {phase}</b> · {aname}</div>"
        )
    agent_panel.markdown("\n".join(rows), unsafe_allow_html=True)


def add_log(level: str, agent: str, message: str):
    now  = datetime.now().strftime("%H:%M:%S")
    icon = {"info": "ℹ️", "success": "✅", "warn": "⚠️", "error": "❌"}.get(level, "ℹ️")
    log_lines.append(f"`{now}` {icon} **[{agent}]** {message}")
    log_placeholder.markdown("\n\n".join(log_lines[-40:]))


render_agents()


# ── 비동기 실행 ──────────────────────────────────────────────────────
from backend.models.schemas import ResearchScope, WSMessage, WSMessageType

scope = ResearchScope(
    topic=topic,
    industries=industries,
    target_companies=target_companies,
    date_range_days=date_range,
)


async def run_analysis():
    from backend.orchestrator.mi_orchestrator import MIOrchestrator

    orch = MIOrchestrator(api_key=api_key)

    async def ws_cb(msg: WSMessage):
        aid   = msg.agent_id or ""
        aname = msg.agent_name or "시스템"
        pct   = msg.progress_pct or 0

        if msg.type == WSMessageType.AGENT_START:
            agent_states[aid] = "running"
            render_agents()
            progress_bar.progress(max(int(pct), 2), text=f"{aname} 실행 중...")
            add_log("info", aname, "시작")

        elif msg.type == WSMessageType.AGENT_PROGRESS:
            progress_bar.progress(max(int(pct), 2), text=f"{aname}: {msg.message or ''}")

        elif msg.type == WSMessageType.AGENT_COMPLETE:
            agent_states[aid] = "done"
            render_agents()
            dp  = (msg.data or {}).get("data_points", 0)
            dur = (msg.data or {}).get("duration", 0)
            progress_bar.progress(int(pct), text=f"{aname} 완료 ({pct:.0f}%)")
            add_log("success", aname, f"완료 — {dp}개 데이터, {dur:.1f}초")

        elif msg.type == WSMessageType.AGENT_ERROR:
            agent_states[aid] = "error"
            render_agents()
            add_log("error", aname, msg.message or "오류 발생")

        elif msg.type == WSMessageType.SESSION_COMPLETE:
            progress_bar.progress(100, text="✅ 분석 완료!")
            add_log("success", "시스템", "MI 분석 완료!")

        elif msg.type == WSMessageType.LOG:
            add_log("info", "시스템", msg.message or "")

    orch.set_ws_callback(ws_cb)
    return await orch.run(scope=scope, session_id="streamlit-run")


session = asyncio.run(run_analysis())

progress_bar.progress(100, text="✅ 분석 완료!")
st.success(f"분석 완료!")
st.divider()

# ── 결과 탭 ──────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📋 Executive Summary", "📄 전체 리포트", "🔍 에이전트별 결과"])

with tab1:
    st.markdown(session.executive_summary or "요약 없음")

with tab2:
    report_md = session.final_report or ""
    st.download_button(
        "⬇️ Markdown 다운로드",
        data=report_md.encode("utf-8"),
        file_name=f"MI_{topic[:20].replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.md",
        mime="text/markdown",
    )
    st.markdown(report_md)

with tab3:
    for aid, aname, phase in AGENT_ORDER:
        if aid not in session.agent_results:
            continue
        output  = session.agent_results[aid]
        quality = output.quality.overall.value if output.quality else "unknown"
        badge   = {"pass": "🟢", "warning": "🟡", "fail": "🔴"}.get(quality, "⚪")
        with st.expander(f"{badge} Phase {phase} · {aname}"):
            c1, c2, c3 = st.columns(3)
            c1.metric("수집 데이터", f"{output.data_points_collected}건")
            c2.metric("소요 시간",   f"{output.duration_seconds:.1f}초")
            c3.metric("품질",        quality.upper())
            st.caption(f"**요약**: {output.summary}")
            st.divider()
            st.markdown(output.analysis or "분석 내용 없음")
