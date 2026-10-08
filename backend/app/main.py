# backend/app/main.py
import sys
import os
from fastapi import Response



# ----------------------------
# Add project root to Python path
# ----------------------------
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

import threading

# ----------------------------
# Imports
# ----------------------------
from fastapi import Depends, FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
import json

from app.services.intent_router import analyze_intent, stream_analyze_intent
from app.services.rate_limiter import check_rate_limit
from app.services.session_manager import get_session
from app.utils.auth import get_current_user
from app.api import auth
from app.api.voice import router as audio_router
from app.api.counselor import router as counselor_router
from app.api.session import router as session_router
from app.api.research import router as research_router

# Security: the interactive Swagger UI (/docs) and raw OpenAPI schema
# (/openapi.json) are open by default in FastAPI, which leaks internal data
# models, field names, and developer notes to anyone. Disabled unless
# ENVIRONMENT is explicitly set to something other than "production" (e.g.
# for local dev). Set ENVIRONMENT=production in the Replit deployment's
# secrets to turn this on for the live backend.
_IS_PROD = os.getenv("ENVIRONMENT", "production").lower() == "production"

app = FastAPI(
    title="GAIDA Backend",
    docs_url=None if _IS_PROD else "/docs",
    redoc_url=None if _IS_PROD else "/redoc",
    openapi_url=None if _IS_PROD else "/openapi.json",
)


# ----------------------------
# Pre-warm cold-start dependencies
# ----------------------------
#
# Deliberately NOT on the startup critical path.
#
# Uvicorn does not serve a single request until the startup event returns: it
# prints "Waiting for application startup." and holds there. Anything slow in
# here delays (and can indefinitely block) the deployment's healthcheck, which
# is how a healthy app gets reported as failed on deploy.
#
# All three steps hit the network or load ~50MB of pickles, and the Supabase
# calls are bare `.execute()` with no timeout. try/except handles a call that
# *fails*, but not one that *hangs* — so a stalled request would previously
# leave the process alive, answering nothing, while healthchecks piled up
# against it. Moving the work to a daemon thread means "Application startup
# complete." prints in milliseconds regardless, and a hung warm call costs
# nothing but one thread.
_PREWARM_DONE = {"ml": False, "supabase": False, "alerts": False}


def _prewarm():
    # 1. Pre-load ML classifier models
    try:
        from app.services.ml_classifier import _load_all_models
        _load_all_models()
        _PREWARM_DONE["ml"] = True
        print("[startup] ML models loaded")
    except Exception as e:
        print(f"[startup] ML model load skipped: {e}")

    # 2. Warm Supabase connection pool
    try:
        from app.database.database import supabase
        supabase.table("sessions").select("id").limit(1).execute()
        _PREWARM_DONE["supabase"] = True
        print("[startup] Supabase connection warmed")
    except Exception as e:
        print(f"[startup] Supabase warm skipped: {e}")

    # 3. Rehydrate pending counselor alerts so no alert disappears on restart,
    #    and start the escalation-deadline monitor that re-notifies
    #    unacknowledged Crisis/High alerts until a human responds.
    try:
        from app.api.counselor import _hydrate_alerts, _start_escalation_monitor
        _hydrate_alerts()
        _start_escalation_monitor()
        _PREWARM_DONE["alerts"] = True
        print("[startup] alert hydration + escalation monitor started")
    except Exception as e:
        print(f"[startup] escalation monitor start skipped: {e}")


@app.on_event("startup")
def prewarm():
    threading.Thread(target=_prewarm, name="gaida-prewarm", daemon=True).start()


# ----------------------------
# Routers
# ----------------------------
app.include_router(auth.router)
app.include_router(audio_router)
app.include_router(counselor_router)
app.include_router(session_router)
app.include_router(research_router)

# ----------------------------
# CORS
# ----------------------------
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://gaida-system.vercel.app",
]

# Also allow the Vite dev server when it's reached over the local network
# (e.g. http://192.168.1.23:5173) — this is what lets a phone on the same
# Wi-Fi test against `npm run dev -- --host` without editing this list by
# hand every time your PC's LAN IP changes. Private ranges only (RFC 1918),
# so this never opens CORS to the public internet.
_LAN_ORIGIN_REGEX = (
    r"^http://("
    r"192\.168\.\d{1,3}\.\d{1,3}"
    r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}"
    r"):5173$"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=_LAN_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Security headers
# ----------------------------
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# ----------------------------
# Models
# ----------------------------
class UserInput(BaseModel):
    message: str
    session_id: str | None = None
    user_id: str | None = None
    intent: str | None = None
    vent_mode: bool = False

# ----------------------------
# Routes
# ----------------------------

@app.head("/")
def root_head():
    return Response(status_code=200)


@app.get("/")
def root():
    return {"status": "ok", "message": "GAIDA Backend"}


# Healthcheck endpoint for the deploy platform.
#
# Always 200 once the process is serving — intentionally, and this is the whole
# point of it existing. A healthcheck that reflected warm-up state would fail
# forever if warm-up stalls, which is precisely the outage shape we are
# defending against: the process is up and can answer requests, so it is
# healthy. Readiness is reported in the body instead, where a human reading
# the response can see it without it ever gating the deployment.
#
# HEAD is registered explicitly because FastAPI does not auto-add HEAD for a
# GET route, and several platforms probe with HEAD.
@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "GAIDA Backend",
        "warmup": dict(_PREWARM_DONE),
    }


@app.head("/health")
def health_head():
    return Response(status_code=200)


@app.post("/virtual-agent")
def virtual_agent(input: UserInput, user: dict = Depends(get_current_user)):
    check_rate_limit(user["user_id"])

    if input.session_id:
        session = get_session(input.session_id)
        if session and session.get("user_id") and session["user_id"] != user["user_id"]:
            raise HTTPException(status_code=403, detail="Session does not belong to this user")

    result = analyze_intent(
        user_message=input.message,
        session_id=input.session_id,
        user_id=user["user_id"],
        vent_mode=input.vent_mode,
    )

    if result.get("counselor_active"):
        return {
            "session_id": result.get("session_id"),
            "counselor_active": True,
            "response": None,
        }

    return {
        "session_id": result.get("session_id"),
        "intent": result.get("intent"),
        "confidence": result.get("confidence"),
        "anxiety_level": result.get("anxiety_level"),
        "severity": result.get("severity"),
        "anxiety_score": result.get("anxiety_score"),
        "response": result.get("response"),
        "method": result.get("method"),
        "crisis_hold": result.get("crisis_hold", False),
    }


def _auth_guard(input: UserInput, user: dict):
    """Shared auth + session-ownership checks for the chat endpoints."""
    check_rate_limit(user["user_id"])

    if input.session_id:
        session = get_session(input.session_id)
        if session and session.get("user_id") and session["user_id"] != user["user_id"]:
            raise HTTPException(status_code=403, detail="Session does not belong to this user")


def _stream_agent_events(message: str, session_id: str | None, user_id: str, vent_mode: bool):
    """Converts stream_analyze_intent event dicts into NDJSON lines."""
    for event in stream_analyze_intent(
        user_message=message,
        session_id=session_id,
        user_id=user_id,
        vent_mode=vent_mode,
    ):
        yield json.dumps(event, ensure_ascii=False) + "\n"


@app.post("/virtual-agent/stream")
def virtual_agent_stream(input: UserInput, user: dict = Depends(get_current_user)):
    """Streaming chat endpoint. Emits NDJSON dicts, one per line:
      {"type": "delta", "text": "<token chunk>"}
      {"type": "done",  "result": {...}}
    """
    _auth_guard(input, user)
    return StreamingResponse(
        _stream_agent_events(input.message, input.session_id, user["user_id"], input.vent_mode),
        media_type="application/x-ndjson",
    )