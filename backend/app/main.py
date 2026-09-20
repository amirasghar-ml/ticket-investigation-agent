from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import ROOT_DIR
from app.demo import ERROR_METRICS, SERVICE_STATUS, USERS
from app.demo.seed import seed
from app.models import TicketRequest
from app.agent.orchestrator import run_investigation

seed()

app = FastAPI(title="Support Ticket Agent", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True, "service": "support-ticket-agent"}


@app.post("/api/investigate")
async def investigate(request: TicketRequest):
    async def stream():
        async for event in run_investigation(request):
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@app.get("/internal/services/status")
def services_status():
    return {"services": SERVICE_STATUS}


@app.get("/internal/auth/metrics")
def auth_metrics():
    return ERROR_METRICS


@app.get("/internal/users/{email}")
def user_profile(email: str):
    user = next((item for item in USERS if item["email"].lower() == email.lower()), None)
    if not user:
        return {"user": None}
    return {"user": user}


frontend_dist = ROOT_DIR / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
