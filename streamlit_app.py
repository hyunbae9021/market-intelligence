"""
Market Intelligence AI — Streamlit Cloud 배포용
"""
from __future__ import annotations

import asyncio
import os
import threading
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

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


# ── 이력 초기화 ─────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state["history"] = []

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
        DATE_OPTIONS = {
            "최근 7일": 7,
            "최근 30일": 30,
            "최근 60일": 60,
            "최근 90일 (1분기)": 90,
            "최근 180일 (반기)": 180,
            "최근 365일 (1년)": 365,
            "최근 730일 (2년)": 730,
            "최근 1095일 (3년)": 1095,
        }
        date_label = st.selectbox("분석 기간", list(DATE_OPTIONS.keys()), index=3)
        date_range = DATE_OPTIONS[date_label]

    industries_input = st.text_input("산업 키워드 (쉼표 구분, 선택)",
        placeholder="crypto, fintech, AI, blockchain")

    submitted = st.form_submit_button("🚀 MI 분석 시작", use_container_width=True, type="primary")

# ── 분석 전: 에이전트 소개 + 이력 ──────────────────────────────────
if not submitted or not topic:
    main_tab, history_tab = st.tabs(["🤖 에이전트 구성", "📂 분석 이력"])

    with main_tab:
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

    with history_tab:
        history = st.session_state["history"]
        if not history:
            st.info("아직 분석 기록이 없습니다. 위에서 주제를 입력하고 분석을 시작하세요.")
        else:
            st.markdown(f"### 총 {len(history)}건의 분석 기록")
            for idx, h in enumerate(reversed(history)):
                real_idx = len(history) - 1 - idx
                dur_m = int(h["duration"] // 60)
                dur_s = int(h["duration"] % 60)
                label = f"**{h['date']}** · {h['topic']} · {h['date_range_label']} · {dur_m}분 {dur_s}초 소요"
                with st.expander(label):
                    t1, t2, t3 = st.tabs(["📋 Executive Summary", "📄 전체 리포트", "⬇️ 다운로드"])
                    with t1:
                        st.markdown(h["executive_summary"] or "요약 없음")
                    with t2:
                        st.markdown(h["final_report"] or "")
                    with t3:
                        report_md = h["final_report"] or ""
                        fname = f"MI_{h['topic'][:20].replace(' ','_')}_{h['date'][:10].replace('-','')}.md"
                        st.download_button(
                            "⬇️ Markdown 다운로드",
                            data=report_md.encode("utf-8"),
                            file_name=fname,
                            mime="text/markdown",
                            key=f"dl_{real_idx}",
                        )
                    if st.button("🗑️ 이 기록 삭제", key=f"del_{real_idx}"):
                        st.session_state["history"].pop(real_idx)
                        st.rerun()

    st.stop()


# ── 분석 실행 ────────────────────────────────────────────────────────
target_companies = [c.strip() for c in companies_input.split(",") if c.strip()]
industries = [i.strip() for i in industries_input.split(",") if i.strip()] or \
             ["crypto", "fintech", "AI"]

start_time = datetime.now()
st.markdown(f"## 📊 {topic}")

# 상단 상태 바
status_col1, status_col2, status_col3, status_col4 = st.columns(4)
status_badge  = status_col1.empty()
current_agent = status_col2.empty()
done_count    = status_col4.empty()

status_badge.info("🔄 **분석 실행 중**")
current_agent.caption("현재: 준비 중...")
done_count.caption("완료: 0 / 14")

# JavaScript 타이머 — 브라우저에서 1초마다 갱신
_ts = int(start_time.timestamp() * 1000)
with status_col3:
    components.html(f"""
    <div id="mi-timer" style="font-size:13px;color:#555;font-family:sans-serif;padding:4px 0">경과: 0분 0초</div>
    <script>
    var _s={_ts};
    function _tick(){{
        var e=Math.floor((Date.now()-_s)/1000),m=Math.floor(e/60),s=e%60;
        var el=document.getElementById('mi-timer');
        if(el) el.textContent='경과: '+m+'분 '+s+'초';
    }}
    setInterval(_tick,1000); _tick();
    </script>
    """, height=35)

progress_bar    = st.progress(0, text="준비 중...")
agent_panel     = st.empty()
log_expander    = st.expander("📋 실시간 로그", expanded=True)
log_placeholder = log_expander.empty()

agent_states: dict[str, str] = {}
log_lines: list[str] = []
completed = [0]


def render_agents():
    rows = []
    for aid, aname, phase in AGENT_ORDER:
        state = agent_states.get(aid, "pending")
        css  = {"pending": "agent-pending", "running": "agent-running",
                "done": "agent-done", "error": "agent-error"}.get(state, "agent-pending")
        icon = {"pending": "○", "running": "⟳", "done": "✓", "error": "✗"}.get(state, "○")
        rows.append(
            f"<div class='agent-row {css}'>{icon} <b>Phase {phase}</b> · {aname}</div>"
        )
    agent_panel.markdown("\n".join(rows), unsafe_allow_html=True)


def add_log(level: str, agent: str, message: str):
    now  = datetime.now().strftime("%H:%M:%S")
    icon = {"info": "ℹ️", "success": "✅", "warn": "⚠️", "error": "❌"}.get(level, "ℹ️")
    log_lines.append(f"`{now}` {icon} **[{agent}]** {message}")
    log_placeholder.markdown("\n\n".join(log_lines[-50:]))


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
            progress_bar.progress(max(int(pct), 2), text=f"⟳ {aname} 실행 중...")
            current_agent.caption(f"현재: **{aname}**")
            add_log("info", aname, "시작")

        elif msg.type == WSMessageType.AGENT_PROGRESS:
            progress_bar.progress(max(int(pct), 2), text=f"⟳ {aname}: {msg.message or ''}")
            current_agent.caption(f"현재: **{aname}** — {msg.message or ''}")

        elif msg.type == WSMessageType.AGENT_COMPLETE:
            agent_states[aid] = "done"
            completed[0] += 1
            render_agents()
            dp  = (msg.data or {}).get("data_points", 0)
            dur = (msg.data or {}).get("duration", 0)
            progress_bar.progress(int(pct), text=f"✓ {aname} 완료 ({pct:.0f}%)")
            done_count.caption(f"완료: **{completed[0]} / 14**")
            add_log("success", aname, f"완료 — {dp}개 데이터, {dur:.1f}초")

        elif msg.type == WSMessageType.AGENT_ERROR:
            agent_states[aid] = "error"
            render_agents()
            add_log("error", aname, msg.message or "오류 발생")

        elif msg.type == WSMessageType.SESSION_COMPLETE:
            progress_bar.progress(100, text="✅ 분석 완료!")
            status_badge.success("✅ **분석 완료**")
            current_agent.caption("모든 에이전트 완료")
            done_count.caption(f"완료: **14 / 14**")
            add_log("success", "시스템", "MI 분석 완료!")

        elif msg.type == WSMessageType.LOG:
            add_log("info", "시스템", msg.message or "")

    orch.set_ws_callback(ws_cb)
    return await orch.run(scope=scope, session_id="streamlit-run")


# ── 백그라운드 스레드에서 asyncio 실행 (Streamlit Cloud 호환) ──────────
_ctx = get_script_run_ctx()
_result: dict = {"session": None, "error": None}
_done = threading.Event()


def _run_analysis_thread():
    add_script_run_ctx(threading.current_thread(), _ctx)
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    try:
        _result["session"] = _loop.run_until_complete(run_analysis())
    except Exception as exc:
        _result["error"] = exc
    finally:
        try:
            _loop.close()
        except Exception:
            pass
        _done.set()


_t = threading.Thread(target=_run_analysis_thread, daemon=True)
_t.start()
_done.wait()

if _result["error"]:
    import traceback as _tb
    st.error(f"분석 실행 오류: {_result['error']}")
    st.code(_tb.format_exc())
    st.stop()

session = _result["session"]

# ── 분석 이력 저장 ───────────────────────────────────────────────────
duration_sec = (datetime.now() - start_time).total_seconds()
st.session_state["history"].append({
    "topic": topic,
    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "date_range_label": date_label,
    "date_range": date_range,
    "duration": duration_sec,
    "executive_summary": session.executive_summary,
    "final_report": session.final_report,
})

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
