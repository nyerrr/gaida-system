# backend/app/main.py
import sys
import os
from pathlib import Path
import json
from datetime import datetime

# ----------------------------
# Add project root to Python path
# ----------------------------
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

# ----------------------------
# Imports
# ----------------------------
from backend.app.services.rate_limiter import check_rate_limit
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.services.intent_router import analyze_intent
from app.api import auth
from app.api.voice import router as audio_router

app = FastAPI(title="GAIDA Backend")

# Include API routers
app.include_router(auth.router)
app.include_router(audio_router)

# Enable CORS for local frontend during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# accept optional session_id
class UserInput(BaseModel):
    message: str
    session_id: str | None = None

# ----------------------------
# Logging setup
# ----------------------------
LOG_FILE = Path("logs/interactions.json")
LOG_FILE.parent.mkdir(exist_ok=True)
if not LOG_FILE.exists():
    LOG_FILE.write_text("[]")


def log_interaction(
    session_id: str,
    user_message: str,
    assistant_reply: str,
    intent: str = None,
    confidence: float = None,
    anxiety_score: int = None,
    method: str = None,
    severity: str = None,
):
    """Append each interaction to interactions.json"""
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
    except json.JSONDecodeError:
        logs = []

    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": session_id,
        "user_message": user_message,
        "assistant_reply": assistant_reply,
    }

    if intent is not None:
        log_entry["intent"] = intent
    if confidence is not None:
        log_entry["confidence"] = confidence
    if anxiety_score is not None:
        log_entry["anxiety_score"] = anxiety_score
    if method is not None:
        log_entry["method"] = method
    if severity is not None:
        log_entry["severity"] = severity

    logs.append(log_entry)

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=4)


# ----------------------------
# Routes
# ----------------------------
@app.get("/")
def root():
    return {"status": "ok", "message": "GAIDA Backend"}



@app.post("/virtual-agent")
def virtual_agent(input: UserInput):

    # Rate limiting
    check_rate_limit(input.session_id or "anonymous")

    # Detect intent + anxiety level + generate GPT response
    result = analyze_intent(
        user_message=input.message,
        session_id=input.session_id,
    )

    # Log interaction
    log_interaction(
        session_id=result.get("session_id") or input.session_id or "unknown",
        user_message=input.message,
        assistant_reply=result.get("response", ""),
        intent=result.get("intent"),
        confidence=result.get("confidence"),
        anxiety_score=result.get("anxiety_score"),
        method=result.get("method"),
        severity=result.get("severity"),
    )

    # Return response to frontend
    # NOTE: severity is now included so the sidebar updates correctly
    return {
        "session_id": result.get("session_id"),
        "intent": result.get("intent"),
        "confidence": result.get("confidence"),
        "anxiety_level": result.get("anxiety_level"),
        "severity": result.get("severity"),        # ← was missing before, now included
        "anxiety_score": result.get("anxiety_score"),
        "response": result.get("response"),
        "method": result.get("method"),
    }