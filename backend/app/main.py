# backend/app/main.py
import sys
import os
from datetime import datetime
from app.database.database import supabase
from fastapi import Response



# ----------------------------
# Add project root to Python path
# ----------------------------
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

# ----------------------------
# Imports
# ----------------------------
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


from app.services.intent_router import analyze_intent
from app.services.rate_limiter import check_rate_limit
from app.utils.consent_checker import log_consent
from app.api import auth
from app.api.voice import router as audio_router
from app.api.counselor import router as counselor_router
from app.api.session import router as session_router

app = FastAPI(title="GAIDA Backend")

# ----------------------------
# Routers
# ----------------------------
app.include_router(auth.router)
app.include_router(audio_router)
app.include_router(counselor_router)
app.include_router(session_router)

# ----------------------------
# CORS
# ----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Models
# ----------------------------
class UserInput(BaseModel):
    message: str
    session_id: str | None = None
    user_id: str | None = None
    intent: str | None = None
    vent_mode: bool = False

class ConsentInput(BaseModel):
    session_id: str
    consent_given: bool


# ----------------------------
# Routes
# ----------------------------

@app.head("/")
def root_head():
    return Response(status_code=200)


@app.get("/")
def root():
    return {"status": "ok", "message": "GAIDA Backend"}


@app.post("/consent")
def record_consent(input: ConsentInput):
    log_consent(session_id=input.session_id, consent_given=input.consent_given)
    return {
        "status": "ok",
        "session_id": input.session_id,
        "consent_given": input.consent_given,
    }


@app.post("/virtual-agent")
def virtual_agent(input: UserInput):
    check_rate_limit(input.session_id or "anonymous")

    result = analyze_intent(
        user_message=input.message,
        session_id=input.session_id,
        user_id=input.user_id,
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
    }