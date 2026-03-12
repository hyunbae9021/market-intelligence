"""
Market Intelligence AI — Streamlit Cloud 배포용
"""
from __future__ import annotations

import asyncio
import io
import os
import re
import threading
import time
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

.agent-row { padding: 6px 14px; border-radius: 8px; margin: 3px 0; font-size: 14px; transition: all 0.3s ease; }
.agent-done    { background: #F0FDF4; border-left: 3px solid #0ABF76; }
.agent-pending { background: #F1F5F9; border-left: 3px solid #CBD5E1; color: #94A3B8; }
.agent-error   { background: #FFF1F2; border-left: 3px solid #F04452; }

@keyframes pulse-border {
  0%,100% { border-left-color: #1B3BFF; background: #EEF2FF; }
  50%      { border-left-color: #7C9FFF; background: #F5F7FF; }
}
@keyframes spin {
  from { display:inline-block; transform: rotate(0deg); }
  to   { display:inline-block; transform: rotate(360deg); }
}
.agent-running {
  background: #EEF2FF;
  border-left: 3px solid #1B3BFF;
  animation: pulse-border 1.6s ease-in-out infinite;
}
.agent-running .spin-icon {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes blink {
  0%,80%,100% { opacity: 0.2; transform: scale(0.8); }
  40%         { opacity: 1;   transform: scale(1.1); }
}
.dot-pulse span {
  display: inline-block; width: 6px; height: 6px;
  border-radius: 50%; background: #1B3BFF; margin: 0 2px;
  animation: blink 1.4s infinite ease-in-out;
}
.dot-pulse span:nth-child(2) { animation-delay: 0.2s; }
.dot-pulse span:nth-child(3) { animation-delay: 0.4s; }

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


# ── PDF 생성 ─────────────────────────────────────────────────────────
def generate_pdf(topic: str, report_md: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import (HRFlowable, Paragraph, SimpleDocTemplate,
                                    Spacer, Table, TableStyle)

    # 한국어 CID 폰트 (ReportLab 내장)
    pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))
    font = "HYSMyeongJo-Medium"

    def S(name, **kw):
        return ParagraphStyle(name, fontName=font, **kw)

    styles = {
        "cover_title": S("ct", fontSize=22, leading=30, spaceAfter=8, textColor=colors.HexColor("#1B3BFF")),
        "cover_sub":   S("cs", fontSize=13, leading=18, spaceAfter=4, textColor=colors.HexColor("#555555")),
        "h1": S("h1", fontSize=15, leading=22, spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#111827")),
        "h2": S("h2", fontSize=12, leading=18, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#1e3a8a")),
        "h3": S("h3", fontSize=11, leading=16, spaceBefore=8,  spaceAfter=3, textColor=colors.HexColor("#374151")),
        "body": S("bd", fontSize=9.5, leading=15, spaceAfter=3),
        "bullet": S("bl", fontSize=9.5, leading=15, spaceAfter=2, leftIndent=14, firstLineIndent=-8),
        "quote": S("qt", fontSize=9.5, leading=15, spaceAfter=3, leftIndent=16,
                   textColor=colors.HexColor("#374151"), borderPad=4),
    }

    def md_inline(text: str) -> str:
        """인라인 마크다운 → ReportLab XML"""
        text = re.sub(r"\*\*\*(.*?)\*\*\*", r"<b><i>\1</i></b>", text)
        text = re.sub(r"\*\*(.*?)\*\*",     r"<b>\1</b>", text)
        text = re.sub(r"\*(.*?)\*",         r"<i>\1</i>", text)
        text = re.sub(r"`(.*?)`",           r"\1", text)
        text = text.replace("&", "&amp;").replace("<b>", "\x00B\x00").replace("</b>", "\x00/B\x00") \
                   .replace("<i>", "\x00I\x00").replace("</i>", "\x00/I\x00")
        text = text.replace("<", "&lt;").replace(">", "&gt;")
        text = text.replace("\x00B\x00", "<b>").replace("\x00/B\x00", "</b>") \
                   .replace("\x00I\x00", "<i>").replace("\x00/I\x00", "</i>")
        return text

    story = []

    # 표지
    story.append(Spacer(1, 2 * cm))
    story.append(Paragraph("Market Intelligence Report", styles["cover_title"]))
    story.append(Paragraph(topic, styles["cover_sub"]))
    story.append(Paragraph(f"작성일: {datetime.now().strftime('%Y년 %m월 %d일')}", styles["cover_sub"]))
    story.append(Paragraph("DUNAMU 경영혁신실 · Confidential", styles["cover_sub"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1B3BFF")))
    story.append(Spacer(1, 0.5 * cm))

    # 본문 파싱
    lines = report_md.split("\n")
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()

        # 구분선
        if re.match(r"^-{3,}$", line):
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=4))
            i += 1
            continue

        # 헤더
        m = re.match(r"^(#{1,3})\s+(.*)", line)
        if m:
            level = len(m.group(1))
            text = md_inline(m.group(2))
            style = {1: "h1", 2: "h2", 3: "h3"}.get(level, "h3")
            story.append(Paragraph(text, styles[style]))
            i += 1
            continue

        # 인용
        if line.startswith("> "):
            story.append(Paragraph(md_inline(line[2:]), styles["quote"]))
            i += 1
            continue

        # 테이블 — 행 단위로 수집
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cols = [c.strip() for c in lines[i].strip().split("|")]
                cols = [c for c in cols if c != ""]  # 앞뒤 빈 셀 제거
                if cols and not re.match(r"^[-:]+$", cols[0]):
                    rows.append(cols)
                i += 1
            if rows:
                max_cols = max(len(r) for r in rows)
                # 열 너비 균등 분배
                col_w = [(14 * cm) / max_cols] * max_cols
                table_data = []
                for r_idx, row in enumerate(rows):
                    padded = row + [""] * (max_cols - len(row))
                    cell_style = styles["body"]
                    table_data.append([Paragraph(md_inline(c), cell_style) for c in padded])
                tbl = Table(table_data, colWidths=col_w, repeatRows=1)
                tbl.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
                    ("TEXTCOLOR",  (0, 0), (-1, 0), colors.HexColor("#1B3BFF")),
                    ("FONTNAME",   (0, 0), (-1, -1), font),
                    ("FONTSIZE",   (0, 0), (-1, -1), 8),
                    ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
                    ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                     [colors.white, colors.HexColor("#F9FAFB")]),
                    ("TOPPADDING",    (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING",   (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
                ]))
                story.append(tbl)
                story.append(Spacer(1, 0.2 * cm))
            continue

        # 불릿
        if re.match(r"^[-*]\s+", line):
            story.append(Paragraph("• " + md_inline(line[2:].strip()), styles["bullet"]))
            i += 1
            continue

        # 번호 목록
        m = re.match(r"^\d+\.\s+(.*)", line)
        if m:
            story.append(Paragraph("• " + md_inline(m.group(1)), styles["bullet"]))
            i += 1
            continue

        # 빈 줄
        if not line:
            story.append(Spacer(1, 0.15 * cm))
            i += 1
            continue

        # 일반 텍스트
        story.append(Paragraph(md_inline(line), styles["body"]))
        i += 1

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=f"MI Report — {topic}",
        author="DUNAMU 경영혁신실",
    )
    doc.build(story)
    return buf.getvalue()


# ── Session state 헬퍼 ────────────────────────────────────────────────
def _add_log(level: str, agent: str, message: str):
    now = datetime.now().strftime("%H:%M:%S")
    icon = {"info": "ℹ️", "success": "✅", "warn": "⚠️", "error": "❌"}.get(level, "ℹ️")
    line = f"`{now}` {icon} **[{agent}]** {message}"
    logs = st.session_state.get("_log_lines", [])
    logs.append(line)
    st.session_state["_log_lines"] = logs[-100:]  # 최대 100줄


def _render_agent_rows() -> str:
    agent_states = st.session_state.get("_agent_states", {})
    rows = []
    for aid, aname, phase in AGENT_ORDER:
        state = agent_states.get(aid, "pending")
        css = {"pending": "agent-pending", "running": "agent-running",
               "done": "agent-done", "error": "agent-error"}.get(state, "agent-pending")
        if state == "running":
            icon_html = "<span class='spin-icon'>⟳</span>"
        else:
            icon_html = {"pending": "○", "done": "✓", "error": "✗"}.get(state, "○")
        rows.append(f"<div class='agent-row {css}'>{icon_html} <b>Phase {phase}</b> · {aname}</div>")
    return "\n".join(rows)


# ── 분석 진행 화면 ────────────────────────────────────────────────────
def show_analysis_screen():
    topic = st.session_state.get("_topic", "")
    is_done = st.session_state.get("_analysis_done", False)
    is_error = st.session_state.get("_analysis_error")
    pct = st.session_state.get("_progress_pct", 0)
    completed_count = st.session_state.get("_completed_count", 0)
    current_agent_name = st.session_state.get("_current_agent", "준비 중...")

    st.markdown(f"## 📊 {topic}")

    status_col1, status_col2, status_col3, status_col4 = st.columns(4)

    if is_done and not is_error:
        status_col1.success("✅ **분석 완료**")
    elif is_error:
        status_col1.error("❌ **분석 실패**")
    else:
        status_col1.markdown(
            "<div style='background:#EEF2FF;border-radius:8px;padding:8px 12px;"
            "font-size:14px;font-weight:600;color:#1B3BFF'>"
            "🔄 분석 실행 중 <span class='dot-pulse'><span></span><span></span><span></span></span></div>",
            unsafe_allow_html=True
        )

    status_col2.caption(f"현재: **{current_agent_name}**")
    status_col4.caption(f"완료: **{completed_count} / 14**")

    _ts = st.session_state.get("_start_time_ts", int(time.time() * 1000))
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

    if is_done:
        st.progress(100, text="✅ 분석 완료!")
    else:
        st.progress(max(int(pct), 1), text=f"⟳ {current_agent_name}... ({pct:.0f}%)")

    st.markdown(_render_agent_rows(), unsafe_allow_html=True)

    with st.expander("📋 실시간 로그", expanded=not is_done):
        log_lines = st.session_state.get("_log_lines", [])
        st.markdown("\n\n".join(log_lines[-50:]) if log_lines else "_로그 없음_")

    if is_error:
        st.error(f"분석 오류: {is_error}")
        if st.button("새 분석 시작"):
            st.session_state["_analysis_active"] = False
            st.rerun()
        return

    if is_done:
        session = st.session_state.get("_analysis_session")
        if not session:
            st.warning("분석 세션 데이터가 없습니다.")
            return

        # 이력 저장 (중복 방지)
        if not st.session_state.get("_history_saved"):
            duration_sec = (time.time() - _ts / 1000)
            st.session_state["history"].append({
                "topic": topic,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "date_range_label": st.session_state.get("_date_label", ""),
                "date_range": st.session_state.get("_date_range", 90),
                "duration": duration_sec,
                "executive_summary": session.executive_summary,
                "final_report": session.final_report,
            })
            st.session_state["_history_saved"] = True

        st.divider()
        tab1, tab2, tab3 = st.tabs(["📋 Executive Summary", "📄 전체 리포트", "🔍 에이전트별 결과"])

        with tab1:
            st.markdown(session.executive_summary or "요약 없음")

        with tab2:
            report_md = session.final_report or ""
            fname_base = f"MI_{topic[:20].replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}"
            dl_col1, dl_col2 = st.columns(2)
            with dl_col1:
                st.download_button(
                    "⬇️ PDF 다운로드",
                    data=generate_pdf(topic, report_md),
                    file_name=f"{fname_base}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                )
            with dl_col2:
                st.download_button(
                    "⬇️ Markdown 다운로드",
                    data=report_md.encode("utf-8"),
                    file_name=f"{fname_base}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            st.markdown(report_md)

        with tab3:
            for aid, aname, phase in AGENT_ORDER:
                if aid not in session.agent_results:
                    continue
                output = session.agent_results[aid]
                quality = output.quality.overall.value if output.quality else "unknown"
                badge = {"pass": "🟢", "warning": "🟡", "fail": "🔴"}.get(quality, "⚪")
                with st.expander(f"{badge} Phase {phase} · {aname}"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("수집 데이터", f"{output.data_points_collected}건")
                    c2.metric("소요 시간",   f"{output.duration_seconds:.1f}초")
                    c3.metric("품질",        quality.upper())
                    st.caption(f"**요약**: {output.summary}")
                    st.divider()
                    st.markdown(output.analysis or "분석 내용 없음")

        st.divider()
        if st.button("🔄 새 분석 시작"):
            st.session_state["_analysis_active"] = False
            st.rerun()
        return

    # 아직 실행 중 — 0.5초 후 재실행
    time.sleep(0.5)
    st.rerun()


# ── 분석 중이면 분석 화면으로 ────────────────────────────────────────
if st.session_state.get("_analysis_active"):
    show_analysis_screen()
    st.stop()


# ── 메인 UI (입력 폼) ────────────────────────────────────────────────
st.markdown("# 📊 Market Intelligence AI")
st.caption("두나무 경영혁신실 · 14개 AI 에이전트 멀티스테이지 분석 플랫폼")
st.divider()

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


# ── 폼 제출 시 분석 시작 ──────────────────────────────────────────────
if submitted and topic:
    target_companies = [c.strip() for c in companies_input.split(",") if c.strip()]
    industries = [i.strip() for i in industries_input.split(",") if i.strip()] or \
                 ["crypto", "fintech", "AI"]

    # Session state 초기화
    st.session_state["_analysis_active"] = True
    st.session_state["_analysis_done"] = False
    st.session_state["_analysis_error"] = None
    st.session_state["_analysis_session"] = None
    st.session_state["_history_saved"] = False
    st.session_state["_topic"] = topic
    st.session_state["_date_label"] = date_label
    st.session_state["_date_range"] = date_range
    st.session_state["_start_time_ts"] = int(time.time() * 1000)
    st.session_state["_agent_states"] = {}
    st.session_state["_log_lines"] = []
    st.session_state["_progress_pct"] = 0
    st.session_state["_current_agent"] = "준비 중..."
    st.session_state["_completed_count"] = 0

    # 백그라운드 스레드 시작
    from backend.models.schemas import ResearchScope, WSMessage, WSMessageType

    scope = ResearchScope(
        topic=topic,
        industries=industries,
        target_companies=target_companies,
        date_range_days=date_range,
    )

    _ctx = get_script_run_ctx()

    async def run_analysis():
        from backend.orchestrator.mi_orchestrator import MIOrchestrator
        orch = MIOrchestrator(api_key=api_key)

        async def ws_cb(msg: WSMessage):
            try:
                aid = msg.agent_id or ""
                aname = msg.agent_name or "시스템"
                pct = msg.progress_pct or 0

                if msg.type == WSMessageType.AGENT_START:
                    st.session_state["_agent_states"][aid] = "running"
                    st.session_state["_current_agent"] = aname
                    _add_log("info", aname, "시작")

                elif msg.type == WSMessageType.AGENT_PROGRESS:
                    st.session_state["_progress_pct"] = pct
                    st.session_state["_current_agent"] = f"{aname} — {msg.message or ''}"

                elif msg.type == WSMessageType.AGENT_COMPLETE:
                    st.session_state["_agent_states"][aid] = "done"
                    st.session_state["_completed_count"] = \
                        st.session_state.get("_completed_count", 0) + 1
                    st.session_state["_progress_pct"] = pct
                    dp = (msg.data or {}).get("data_points", 0)
                    dur = (msg.data or {}).get("duration", 0)
                    _add_log("success", aname, f"완료 — {dp}개 데이터, {dur:.1f}초")

                elif msg.type == WSMessageType.AGENT_ERROR:
                    st.session_state["_agent_states"][aid] = "error"
                    _add_log("error", aname, msg.message or "오류 발생")

                elif msg.type == WSMessageType.SESSION_COMPLETE:
                    st.session_state["_progress_pct"] = 100
                    _add_log("success", "시스템", "MI 분석 완료!")

                elif msg.type == WSMessageType.LOG:
                    _add_log("info", "시스템", msg.message or "")

            except Exception:
                pass  # ws_cb 오류가 분석 스레드에 영향 없도록

        orch.set_ws_callback(ws_cb)
        return await orch.run(scope=scope, session_id="streamlit-run")

    def _run_thread():
        add_script_run_ctx(threading.current_thread(), _ctx)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            session = loop.run_until_complete(run_analysis())
            st.session_state["_analysis_session"] = session
        except Exception as exc:
            st.session_state["_analysis_error"] = str(exc)
        finally:
            try:
                loop.close()
            except Exception:
                pass
            st.session_state["_analysis_done"] = True

    t = threading.Thread(target=_run_thread, daemon=True)
    t.start()

    st.rerun()


# ── 분석 전: 에이전트 소개 + 이력 ──────────────────────────────────
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
                    fname_base = f"MI_{h['topic'][:20].replace(' ','_')}_{h['date'][:10].replace('-','')}"
                    hc1, hc2 = st.columns(2)
                    with hc1:
                        st.download_button(
                            "⬇️ PDF 다운로드",
                            data=generate_pdf(h["topic"], report_md),
                            file_name=f"{fname_base}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            type="primary",
                            key=f"pdf_{real_idx}",
                        )
                    with hc2:
                        st.download_button(
                            "⬇️ Markdown 다운로드",
                            data=report_md.encode("utf-8"),
                            file_name=f"{fname_base}.md",
                            mime="text/markdown",
                            use_container_width=True,
                            key=f"dl_{real_idx}",
                        )
                if st.button("🗑️ 이 기록 삭제", key=f"del_{real_idx}"):
                    st.session_state["history"].pop(real_idx)
                    st.rerun()
