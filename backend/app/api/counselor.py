from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import sys
import os

router = APIRouter(prefix="/api/counselor", tags=["counselor"])

# ---------------------------------------------------------------------------
# Severity mapping
# ---------------------------------------------------------------------------
SEVERITY_MAP = {
    0: "Normal",
    1: "Low",
    3: "Moderate",
    5: "High",
}

def get_severity(anxiety_score: int) -> str:
    return SEVERITY_MAP.get(anxiety_score, "Normal")

def should_alert_counselor(severity: str) -> bool:
    return severity in ("High", "Crisis")

# ---------------------------------------------------------------------------
# In-memory alert store
# ---------------------------------------------------------------------------
ALERTS: list[dict] = []

# ---------------------------------------------------------------------------
# Internal function called by intent_router.py
# ---------------------------------------------------------------------------
def process_alert(
    session_id: str,
    user_id: Optional[str],
    intent: str,
    anxiety_score: int,
    message: str,
) -> dict:
    severity = get_severity(anxiety_score)
    alert_sent = False

    if should_alert_counselor(severity):
        # Check if alert already exists for this session
        existing = next((a for a in ALERTS if a["session_id"] == session_id), None)

        if existing:
            # Update existing alert
            existing["last_message"] = message
            existing["timestamp"] = datetime.utcnow().isoformat()
            existing["intent"] = intent
        else:
            # Create new alert
            alert_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "session_id": session_id,
                "user_id": user_id,
                "intent": intent,
                "anxiety_score": anxiety_score,
                "severity": severity,
                "message": message,
                "last_message": message,
                "status": "pending",
                "counselor_took_over": False,
            }
            ALERTS.append(alert_entry)

            # Save to Supabase
            try:
                from app.database.database import supabase
                supabase.table("counselor_alerts").insert({
                    "session_id": session_id,
                    "user_id": user_id or session_id,
                    "intent": intent,
                    "anxiety_score": anxiety_score,
                    "severity": severity,
                    "message": message,
                    "status": "pending",
                }).execute()
            except Exception as e:
                print(f"Supabase alert insert error: {e}")

        alert_sent = True

    return {
        "severity": severity,
        "alert_sent": alert_sent,
    }

# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

class AlertStatusUpdate(BaseModel):
    session_id: str
    status: str

class TakeOverMessage(BaseModel):
    session_id: str
    message: str


@router.get("/alerts")
def get_alerts():
    """Return all alerts — used by counselor dashboard."""
    return {"alerts": ALERTS, "count": len(ALERTS)}


@router.get("/alerts/pending")
def get_pending_alerts():
    """Return only pending High/Crisis alerts."""
    pending = [a for a in ALERTS if a.get("status") == "pending"]
    return {"alerts": pending, "count": len(pending)}


@router.post("/alerts/update")
def update_alert_status(payload: AlertStatusUpdate):
    """Counselor marks alert as reviewed/resolved/escalated."""
    for alert in ALERTS:
        if alert["session_id"] == payload.session_id:
            alert["status"] = payload.status
            alert["updated_at"] = datetime.utcnow().isoformat()
            # Update Supabase
            try:
                from app.database.database import supabase
                supabase.table("counselor_alerts").update({
                    "status": payload.status,
                }).eq("session_id", payload.session_id).execute()
            except Exception as e:
                print(f"Supabase alert update error: {e}")
            return {"ok": True}
    return {"ok": False, "error": "Alert not found"}


@router.get("/sessions/active")
def get_active_sessions():
    """
    Return all active sessions with severity level.
    Counselor sees severity but NOT chat content unless flagged.
    """
    try:
        from app.services.session_manager import list_active_sessions
        sessions = list_active_sessions()
        result = []
        for s in sessions:
            meta = s.get("meta", {})
            severity = meta.get("severity", "Normal")
            confidence = meta.get("running_confidence", 0.3)

            # Map confidence to severity if not set
            if not severity or severity == "Normal":
                if confidence >= 0.75:
                    severity = "High"
                elif confidence >= 0.60:
                    severity = "Moderate"
                elif confidence >= 0.45:
                    severity = "Low"
                else:
                    severity = "Normal"

            # Check if this session has a pending alert
            has_alert = any(
                a["session_id"] == s["session_id"] and a["status"] == "pending"
                for a in ALERTS
            )

            result.append({
                "session_id": s["session_id"],
                "started_at": s.get("started_at"),
                "message_count": len(s.get("messages", [])),
                "severity": severity,
                "confidence": round(confidence, 3),
                "intent": meta.get("running_intent", "neutral"),
                "has_alert": has_alert,
                "active": s.get("active", True),
            })

        return {"sessions": result, "count": len(result)}
    except Exception as e:
        return {"sessions": [], "count": 0, "error": str(e)}


@router.get("/chat/{session_id}")
def get_chat_transcript(session_id: str):
    """
    Return full chat transcript for a session.
    Only called when counselor clicks View on a flagged alert.
    """
    try:
        from app.services.session_manager import get_session
        session = get_session(session_id)
        if not session:
            return {"error": "Session not found", "messages": []}

        messages = []
        for m in session.get("messages", []):
            messages.append({
                "sender": m.get("sender"),
                "text": m.get("text"),
                "timestamp": m.get("timestamp"),
                "intent": m.get("analysis", {}).get("intent"),
                "confidence": m.get("analysis", {}).get("confidence"),
            })

        return {
            "session_id": session_id,
            "messages": messages,
            "severity": session.get("meta", {}).get("running_confidence", 0.3),
        }
    except Exception as e:
        return {"error": str(e), "messages": []}


@router.post("/takeover")
def counselor_takeover(payload: TakeOverMessage):
    """
    Counselor sends a message directly to the student.
    Injects counselor message into the session.
    """
    try:
        from app.services.session_manager import get_session, record_interaction
        session = get_session(payload.session_id)
        if not session:
            return {"ok": False, "error": "Session not found"}

        # Mark session as counselor-assisted
        if "meta" not in session:
            session["meta"] = {}
        session["meta"]["counselor_active"] = True
        session["meta"]["counselor_message"] = payload.message

        # Record counselor message in session
        record_interaction(
            session_id=payload.session_id,
            sender="counselor",
            text=payload.message,
            analysis={"intent": "counselor_intervention"},
            response=None,
        )

        # Mark alert as escalated
        for alert in ALERTS:
            if alert["session_id"] == payload.session_id:
                alert["status"] = "escalated"
                alert["counselor_took_over"] = True
                break

        return {"ok": True, "message": payload.message}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/severity/{anxiety_score}")
def check_severity(anxiety_score: int):
    severity = get_severity(anxiety_score)
    return {
        "anxiety_score": anxiety_score,
        "severity": severity,
        "requires_alert": should_alert_counselor(severity),
    }