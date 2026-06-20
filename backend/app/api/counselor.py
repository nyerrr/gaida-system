from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

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
# In-memory stores
# ---------------------------------------------------------------------------
ALERTS: list[dict] = []
TYPING_STATES: dict = {}  # { session_id: { "counselor": bool, "student": bool } }

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
        existing = next((a for a in ALERTS if a["session_id"] == session_id), None)

        if existing:
            existing["last_message"] = message
            existing["timestamp"] = datetime.utcnow().isoformat()
            existing["intent"] = intent
        else:
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
# Models
# ---------------------------------------------------------------------------
class AlertStatusUpdate(BaseModel):
    session_id: str
    status: str

class TakeOverMessage(BaseModel):
    session_id: str
    message: str

class TypingPayload(BaseModel):
    is_typing: bool
    sender: str  # "counselor" or "student"

class StudentMessage(BaseModel):
    sender: str
    text: str

class CounselorRequest(BaseModel):
    session_id: str
    message: str

class SessionNote(BaseModel):
    session_id: str
    note: str
    outcome: str # e.g. "resolved", "false_alarm", "referred", "follow_up_scheduled"

class ResolveSession(BaseModel):
    session_id: str
    resolved_by: Optional[str] = None

# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@router.post("/sessions/resolve")
def resolve_session(payload: ResolveSession):
    try:
        from app.services.session_manager import get_session
        session = get_session(payload.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if "meta" not in session:
            session["meta"] = {}
        session["meta"]["resolved"] = True
        session["meta"]["resolved_at"] = datetime.utcnow().isoformat()
        session["meta"]["resolved_by"] = payload.resolved_by

        # Also mark the alert as resolved
        for alert in ALERTS:
            if alert["session_id"] == payload.session_id:
                alert["status"] = "resolved"
                alert["resolved_at"] = datetime.utcnow().isoformat()

        try:
            from app.database.database import supabase
            supabase.table("counselor_alerts").update({
                "status": "resolved"
            }).eq("session_id", payload.session_id).execute()
        except Exception as e:
            print(f"Supabase resolve error: {e}")

        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.post("/session-notes")
def add_session_note(payload: SessionNote):
    try:
        from app.database.database import supabase
        supabase.table("session_notes").insert({
            "session_id": payload.session_id,
            "note": payload.note,
            "outcome": payload.outcome,
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.get("/session-notes/{session_id}")
def get_session_notes(session_id: str):
    try:
        from app.database.database import supabase
        result = supabase.table("session_notes").select("*").eq("session_id", session_id).order("created_at", desc=True).execute()
        return {"notes": result.data}
    except Exception as e:
        return {"notes": [], "error": str(e)}
    

@router.get("/alerts")
def get_alerts():
    return {"alerts": ALERTS, "count": len(ALERTS)}


@router.get("/alerts/pending")
def get_pending_alerts():
    pending = [a for a in ALERTS if a.get("status") == "pending"]
    return {"alerts": pending, "count": len(pending)}


@router.post("/alerts/update")
def update_alert_status(payload: AlertStatusUpdate):
    for alert in ALERTS:
        if alert["session_id"] == payload.session_id:
            alert["status"] = payload.status
            alert["updated_at"] = datetime.utcnow().isoformat()
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
    try:
        from app.services.session_manager import list_active_sessions
        sessions = list_active_sessions()
        result = []
        for s in sessions:
            # Skip resolved sessions
            if s.get("meta", {}).get("resolved"):
                continue
            meta = s.get("meta", {})
            severity = meta.get("severity", "Normal")
            confidence = meta.get("running_confidence", 0.3)

            if not severity or severity == "Normal":
                if confidence >= 0.75:
                    severity = "High"
                elif confidence >= 0.60:
                    severity = "Moderate"
                elif confidence >= 0.45:
                    severity = "Low"
                else:
                    severity = "Normal"

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
    Returns full chat transcript including student messages mirrored via POST /chat/{session_id}.
    Also returns typing state for both counselor and student.
    """
    try:
        from app.services.session_manager import get_session
        session = get_session(session_id)
        if not session:
            return {"error": "Session not found", "messages": [], "counselor_typing": False, "student_typing": False}

        messages = []
        for m in session.get("messages", []):
            messages.append({
                "sender": m.get("sender"),
                "text": m.get("text"),
                "timestamp": m.get("timestamp"),
                "intent": m.get("analysis", {}).get("intent"),
                "confidence": m.get("analysis", {}).get("confidence"),
            })

        typing = TYPING_STATES.get(session_id, {})

        return {
            "session_id": session_id,
            "messages": messages,
            "severity": session.get("meta", {}).get("running_confidence", 0.3),
            "counselor_typing": typing.get("counselor", False),
            "student_typing": typing.get("student", False),
            "counselor_active": session.get("meta", {}).get("counselor_active", False),
        }
    except Exception as e:
        return {"error": str(e), "messages": [], "counselor_typing": False, "student_typing": False}


@router.post("/chat/{session_id}")
def post_student_message(session_id: str, payload: StudentMessage):
    """
    Student dashboard mirrors messages here so counselor can see them in real time.
    Called after every student message send.
    """
    try:
        from app.services.session_manager import get_session, record_interaction
        session = get_session(session_id)
        if not session:
            return {"ok": False, "error": "Session not found"}

        record_interaction(
            session_id=session_id,
            sender=payload.sender,
            text=payload.text,
            analysis={},
            response=None,
        )
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/typing/{session_id}")
def set_typing(session_id: str, payload: TypingPayload):
    """Set typing indicator for counselor or student."""
    if session_id not in TYPING_STATES:
        TYPING_STATES[session_id] = {"counselor": False, "student": False}
    TYPING_STATES[session_id][payload.sender] = payload.is_typing
    return {"ok": True}


@router.post("/takeover")
def counselor_takeover(payload: TakeOverMessage):
    """
    Counselor sends a message directly to the student.
    Sets counselor_active = True so VA stops responding.
    """
    try:
        from app.services.session_manager import get_session, record_interaction
        session = get_session(payload.session_id)
        if not session:
            return {"ok": False, "error": "Session not found"}

        if "meta" not in session:
            session["meta"] = {}
        session["meta"]["counselor_active"] = True
        session["meta"]["counselor_message"] = payload.message

        record_interaction(
            session_id=payload.session_id,
            sender="counselor",
            text=payload.message,
            analysis={"intent": "counselor_intervention"},
            response=None,
        )

        for alert in ALERTS:
            if alert["session_id"] == payload.session_id:
                alert["status"] = "escalated"
                alert["counselor_took_over"] = True
                break

        return {"ok": True, "message": payload.message}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.post("/return-to-gaida")
def return_to_gaida(payload: dict):
    from app.services.session_manager import get_session, record_interaction
    
    session_id = payload.get("session_id")
    session = get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if "meta" not in session:
        session["meta"] = {}
    
    session["meta"]["counselor_active"] = False
    
    record_interaction(
        session_id=session_id,
        sender="system",
        text="Counselor returned the conversation to GAIDA.",
        analysis={},
        response=None,
    )
    
    return {"ok": True, "session_id": session_id}


@router.get("/severity/{anxiety_score}")
def check_severity(anxiety_score: int):
    severity = get_severity(anxiety_score)
    return {
        "anxiety_score": anxiety_score,
        "severity": severity,
        "requires_alert": should_alert_counselor(severity),
    }

@router.get("/analytics/overview")
def get_analytics_overview():
    try:
        from app.database.database import supabase
        from datetime import datetime, timedelta

        # Anxiety distribution from interactions
        interactions = supabase.table("interactions").select("severity").execute()
        severity_counts = {"Low": 0, "Moderate": 0, "High": 0, "Normal": 0}
        for row in interactions.data:
            s = row.get("severity", "Normal") or "Normal"
            if s in severity_counts:
                severity_counts[s] += 1

        # Sessions this week
        week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        sessions = supabase.table("sessions").select("created_at").gte("created_at", week_ago).execute()

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        week_data = {d: 0 for d in days}
        for row in sessions.data:
            if row.get("created_at"):
                day = datetime.fromisoformat(row["created_at"]).strftime("%a")
                if day in week_data:
                    week_data[day] += 1

        # Alerts per month
        alerts = supabase.table("counselor_alerts").select("created_at, severity").execute()

        return {
            "anxiety_distribution": [
                {"name": k, "value": v} for k, v in severity_counts.items() if v > 0
            ],
            "sessions_this_week": [
                {"day": d, "count": week_data[d]} for d in days
            ],
            "total_sessions": len(supabase.table("sessions").select("id").execute().data),
            "total_alerts": len(alerts.data),
        }
    except Exception as e:
        return {"error": str(e)}

@router.post("/request-counselor")
def request_counselor(payload: CounselorRequest):
    try:
        existing = next((a for a in ALERTS if a["session_id"] == payload.session_id), None)
        if existing:
            existing["last_message"] = payload.message
            existing["timestamp"] = datetime.utcnow().isoformat()
        else:
            alert_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "session_id": payload.session_id,
                "user_id": None,
                "intent": "student_requested",
                "anxiety_score": 0,
                "severity": "Requested",
                "message": payload.message,
                "last_message": payload.message,
                "status": "pending",
                "counselor_took_over": False,
            }
            ALERTS.append(alert_entry)

            try:
                from app.database.database import supabase
                supabase.table("counselor_alerts").insert({
                    "session_id": payload.session_id,
                    "user_id": payload.session_id,
                    "intent": "student_requested",
                    "anxiety_score": 0,
                    "severity": "Requested",
                    "message": payload.message,
                    "status": "pending",
                }).execute()
            except Exception as e:
                print(f"Supabase alert insert error: {e}")

        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}