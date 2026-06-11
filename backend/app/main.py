import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from app.agents.orchestrator import create_session, get_session
from app.capabilities import get_runtime_capabilities
from app.config import settings
from app.gcp_runtime import configure_gcp_runtime, gemini_backend
from app.tools.fivetran_mcp_stdio import close_fivetran_mcp
from app.models import ApprovalDecision, MissionRequest, MissionResponse


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_gcp_runtime()
    yield
    await close_fivetran_mcp()


app = FastAPI(
    title="OpenAid Provisioner",
    description="Humanitarian data provisioning agent — Google Cloud Rapid Agent Hackathon",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "build_phase": 2,
        "gemini_model": settings.gemini_model,
        "gemini_backend": gemini_backend(),
        "gcp_project": settings.google_cloud_project or None,
        "capabilities": get_runtime_capabilities(),
    }


@app.post("/api/missions", response_model=MissionResponse)
async def start_mission(body: MissionRequest):
    session = create_session(body.prompt)
    asyncio.create_task(session.run())
    return MissionResponse(session_id=session.id, steps=session.steps)


@app.get("/api/missions/{session_id}/stream")
async def stream_mission(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        async for item in session.events():
            if isinstance(item, str):
                if item == "__DONE__":
                    payload = {
                        "type": "done",
                        "briefing": session.briefing,
                        "steps": [s.model_dump() for s in session.steps],
                    }
                    yield {"event": "done", "data": json.dumps(payload)}
                continue

            if hasattr(item, "model_dump"):
                kind = "approval" if item.__class__.__name__ == "ApprovalRequest" else "step"
                yield {"event": kind, "data": json.dumps(item.model_dump(), default=str)}

    return EventSourceResponse(event_generator())


@app.post("/api/missions/{session_id}/approve")
async def approve_mission(session_id: str, body: ApprovalDecision):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.approval:
        raise HTTPException(status_code=400, detail="No pending approval")

    session.approval_decision = body.approved
    session.approval_event.set()
    return {"status": "approved" if body.approved else "rejected"}


@app.get("/api/missions/{session_id}")
async def get_mission(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return MissionResponse(
        session_id=session.id,
        briefing=session.briefing,
        steps=session.steps,
    )
