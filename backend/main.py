"""
Market Intelligence 멀티 에이전트 시스템 - FastAPI 서버
WebSocket 기반 실시간 에이전트 진행 상황 스트리밍
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.config import ANTHROPIC_API_KEY, COINGECKO_API_KEY, DART_API_KEY, GITHUB_TOKEN
from backend.models.schemas import MISession, ResearchScope, SessionStatus, WSMessage, WSMessageType
from backend.orchestrator.mi_orchestrator import MIOrchestrator
from backend.utils.pdf_renderer import agent_to_print_html, markdown_to_print_html

app = FastAPI(
    title="Market Intelligence Multi-Agent System",
    description="14개 AI 에이전트가 협력하는 Market Intelligence 분석 플랫폼",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 (프론트엔드)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# ── 인메모리 세션 저장소 ──
_sessions: Dict[str, MISession] = {}
# ── 실행 중인 태스크 저장소 (취소용) ──
_running_tasks: Dict[str, asyncio.Task] = {}

# ── WebSocket 연결 관리 ──
class ConnectionManager:
    def __init__(self):
        self._connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        if session_id not in self._connections:
            self._connections[session_id] = []
        self._connections[session_id].append(ws)

    def disconnect(self, session_id: str, ws: WebSocket):
        if session_id in self._connections:
            self._connections[session_id].remove(ws)

    async def broadcast(self, session_id: str, message: WSMessage):
        if session_id not in self._connections:
            return
        data = message.model_dump_json()
        dead = []
        for ws in self._connections[session_id]:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[session_id].remove(ws)


manager = ConnectionManager()


# ── REST API ──

class StartRequest(BaseModel):
    topic: str
    industries: List[str] = []
    target_companies: List[str] = []
    regions: List[str] = ["KR", "US", "Global"]
    date_range_days: int = 90
    custom_instructions: Optional[str] = None


@app.get("/")
async def root():
    """프론트엔드 서빙"""
    return FileResponse("frontend/index.html")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "api_key_set": bool(ANTHROPIC_API_KEY),
    }


@app.get("/api/agents")
async def get_agents():
    """14개 에이전트 명세 반환"""
    if not ANTHROPIC_API_KEY:
        # API 키 없어도 명세는 반환 가능
        dummy_key = "dummy"
    else:
        dummy_key = ANTHROPIC_API_KEY

    orchestrator = MIOrchestrator(api_key=dummy_key)
    return {"agents": orchestrator.get_all_agent_specs()}


@app.post("/api/sessions")
async def create_session(req: StartRequest):
    """새 MI 분석 세션 생성"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="ANTHROPIC_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.",
        )

    session_id = str(uuid.uuid4())
    scope = ResearchScope(
        topic=req.topic,
        industries=req.industries,
        target_companies=req.target_companies,
        regions=req.regions,
        date_range_days=req.date_range_days,
        custom_instructions=req.custom_instructions,
    )

    session = MISession(session_id=session_id, scope=scope)
    _sessions[session_id] = session

    return {"session_id": session_id, "status": "created"}


@app.post("/api/sessions/{session_id}/run")
async def run_session(session_id: str):
    """세션 분석 실행 (비동기 - WebSocket으로 진행 상황 수신)"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    session = _sessions[session_id]

    orchestrator = MIOrchestrator(api_key=ANTHROPIC_API_KEY)

    async def ws_callback(msg: WSMessage):
        await manager.broadcast(session_id, msg)

    orchestrator.set_ws_callback(ws_callback)

    task = asyncio.create_task(
        _run_analysis(orchestrator, session, session_id)
    )
    _running_tasks[session_id] = task

    return {"status": "running", "session_id": session_id}


async def _run_analysis(orchestrator: MIOrchestrator, session: MISession, session_id: str):
    """백그라운드 분석 실행"""
    try:
        completed_session = await orchestrator.run(
            scope=session.scope,
            session_id=session_id,
        )
        _sessions[session_id] = completed_session
    except asyncio.CancelledError:
        session.status = SessionStatus.CANCELLED
        _sessions[session_id] = session
        await manager.broadcast(session_id, WSMessage(
            type=WSMessageType.SESSION_CANCELLED,
            session_id=session_id,
            message="분석이 사용자에 의해 중지되었습니다.",
        ))
    except Exception as e:
        session.status = SessionStatus.FAILED
        _sessions[session_id] = session
    finally:
        _running_tasks.pop(session_id, None)


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """세션 상태 및 결과 조회"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    session = _sessions[session_id]
    return {
        "session_id": session.session_id,
        "status": session.status.value,
        "progress_pct": session.progress_pct,
        "current_phase": session.current_phase,
        "current_agent": session.current_agent,
        "created_at": session.created_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "total_tokens_used": session.total_tokens_used,
        "agents_completed": len(session.agent_results),
    }


@app.post("/api/sessions/{session_id}/cancel")
async def cancel_session(session_id: str):
    """분석 중지"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    task = _running_tasks.get(session_id)
    if task and not task.done():
        task.cancel()
        return {"status": "cancelling", "session_id": session_id}
    else:
        return {"status": "not_running", "session_id": session_id}


@app.get("/api/sessions/{session_id}/report")
async def get_report(session_id: str):
    """최종 리포트 조회"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    session = _sessions[session_id]
    return {
        "session_id": session_id,
        "final_report": session.final_report,
        "executive_summary": session.executive_summary,
        "dashboard_data": session.dashboard_data,
    }


@app.get("/api/sessions/{session_id}/agents/{agent_id}")
async def get_agent_result(session_id: str, agent_id: str):
    """특정 에이전트 결과 조회"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    session = _sessions[session_id]
    if agent_id not in session.agent_results:
        raise HTTPException(status_code=404, detail="에이전트 결과를 찾을 수 없습니다.")

    output = session.agent_results[agent_id]
    return output.model_dump()


# ── 인쇄/PDF 엔드포인트 ──────────────────────────────────────────────

@app.get("/api/sessions/{session_id}/report/print", response_class=HTMLResponse)
async def get_report_print(session_id: str):
    """전체 리포트 — 인쇄/PDF 저장용 HTML"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    session = _sessions[session_id]
    topic = session.scope.topic
    report_md = session.final_report or session.executive_summary or "분석이 아직 완료되지 않았습니다."

    html = markdown_to_print_html(
        markdown_text=report_md,
        title=f"Market Intelligence Report",
        subtitle=topic,
        generated_at=session.completed_at.strftime("%Y년 %m월 %d일") if session.completed_at else "",
    )
    return HTMLResponse(content=html)


@app.get("/api/sessions/{session_id}/report/markdown")
async def get_report_markdown(session_id: str):
    """전체 리포트 — Markdown 다운로드"""
    from fastapi.responses import PlainTextResponse
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    session = _sessions[session_id]
    report_md = session.final_report or session.executive_summary or "분석이 아직 완료되지 않았습니다."
    topic = session.scope.topic
    filename = f"MI_Report_{topic[:20].replace(' ', '_')}.md"
    return PlainTextResponse(
        content=report_md,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        media_type="text/markdown; charset=utf-8",
    )


@app.get("/api/sessions/{session_id}/agents/{agent_id}/print", response_class=HTMLResponse)
async def get_agent_print(session_id: str, agent_id: str):
    """에이전트 결과 — 인쇄/PDF 저장용 HTML"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    session = _sessions[session_id]
    if agent_id not in session.agent_results:
        raise HTTPException(status_code=404, detail="에이전트 결과를 찾을 수 없습니다.")

    output = session.agent_results[agent_id]
    agent_data = output.model_dump()
    html = agent_to_print_html(agent_data, session.scope.topic)
    return HTMLResponse(content=html)


@app.get("/api/sessions/{session_id}/agents/{agent_id}/markdown")
async def get_agent_markdown(session_id: str, agent_id: str):
    """에이전트 결과 — Markdown 다운로드"""
    from fastapi.responses import PlainTextResponse
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    session = _sessions[session_id]
    if agent_id not in session.agent_results:
        raise HTTPException(status_code=404, detail="에이전트 결과를 찾을 수 없습니다.")

    output = session.agent_results[agent_id]
    topic = session.scope.topic
    md = f"""# {output.agent_name}
## {topic}

**Phase**: {output.phase.value}
**상태**: {output.status.value}
**소요 시간**: {output.duration_seconds:.1f}초
**수집 데이터**: {output.data_points_collected}건
**출처**: {', '.join(output.sources_used[:10])}

---

## 요약

{output.summary}

---

## 상세 분석

{output.analysis or '분석 내용 없음'}
"""
    filename = f"{agent_id}_{topic[:20].replace(' ', '_')}.md"
    return PlainTextResponse(
        content=md,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        media_type="text/markdown; charset=utf-8",
    )


@app.get("/api/sessions")
async def list_sessions():
    """세션 목록 조회"""
    return {
        "sessions": [
            {
                "session_id": s.session_id,
                "topic": s.scope.topic,
                "status": s.status.value,
                "created_at": s.created_at.isoformat(),
                "progress_pct": s.progress_pct,
            }
            for s in _sessions.values()
        ]
    }


# ── WebSocket ──

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """실시간 에이전트 진행 상황 스트림"""
    await manager.connect(session_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # 연결 유지
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)


if __name__ == "__main__":
    import uvicorn
    from backend.config import HOST, PORT
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
