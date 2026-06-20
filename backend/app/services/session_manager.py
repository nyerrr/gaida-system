from typing import Dict, Any, List, Callable
from datetime import datetime
import uuid
from app.database.database import supabase
import asyncio

from app.utils.consent_checker import has_consent

SESSIONS: Dict[str, Dict[str, Any]] = {}
SESSION_STALE_MINUTES = 30  # sessions with no activity in this window are excluded from "active"
_SUBSCRIBERS: List[Callable] = []



def start_session(user_id: str | None = None) -> str:
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {
        "session_id": session_id,
        "user_id": user_id,
        "started_at": datetime.utcnow().isoformat() + "Z",
        "messages": [],
        "active": True,
        "meta": {
            # ---------------------------------------------------------------------------
            # Cumulative confidence tracking
            # running_confidence: blended score across all messages in session
            # running_intent: highest distress intent detected so far
            # Starts neutral at 0.3 — builds up or down as conversation progresses
            # ---------------------------------------------------------------------------
            "running_confidence": 0.3,
            "running_intent": "neutral",
            "peak_severity": "Normal",    
            "peak_confidence": 0.3,   
        }
    }
    return session_id


def subscribe(callback: Callable):
    """Register a callback to be invoked on new interactions.

    Callback signature: callback(session_id: str, entry: dict)
    Supports sync or async callables.
    """
    _SUBSCRIBERS.append(callback)


def _notify_subscribers(session_id: str, entry: Dict[str, Any]):
    for cb in list(_SUBSCRIBERS):
        try:
            if asyncio.iscoroutinefunction(cb):
                asyncio.create_task(cb(session_id, entry))
            else:
                cb(session_id, entry)
        except Exception:
            # swallow subscriber errors to avoid breaking main flow
            pass


def _persist_entry(entry: Dict[str, Any]):
    try:
        supabase.table("interactions").insert({
            "session_id": entry.get("session_id"),
            "student_id": entry.get("session_id"),  
            "message": entry.get("text"),
            "response": entry.get("response") or "",
            "timestamp": entry.get("timestamp"),
        }).execute()
    except Exception as e:
        print(f"Supabase insert error: {e}")


def record_interaction(session_id: str, sender: str, text: str, analysis: Dict | None = None, response: str | None = None):
    session = SESSIONS.get(session_id)
    if session is None:
        # create ephemeral session if missing
        session_id = start_session(None)
        session = SESSIONS[session_id]

    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "session_id": session_id,
        "sender": sender,
        "text": text,
        "analysis": analysis or {},
        "response": response,
    }
    session["messages"].append(entry)

    # Update session-level meta (last intent, confidence, intensity, escalate)
    if analysis:
        session["meta"]["last_intent"] = analysis.get("intent")
        session["meta"]["confidence"] = analysis.get("confidence")
        session["meta"]["intensity"] = analysis.get("intensity")
        if analysis.get("escalate"):
            session["meta"]["escalate"] = True

        
        SEVERITY_RANK = {"Normal": 0, "Low": 1, "Moderate": 2, "High": 3, "Crisis": 4}
        new_severity = analysis.get("severity", "Normal")
        new_confidence = analysis.get("confidence", 0.0) or 0.0
        current_peak = session["meta"].get("peak_severity", "Normal")
        if SEVERITY_RANK.get(new_severity, 0) > SEVERITY_RANK.get(current_peak, 0):
            session["meta"]["peak_severity"] = new_severity
            session["meta"]["peak_confidence"] = new_confidence

    # Persist only if consent exists for this session
    try:
        if has_consent(session_id):
            _persist_entry(entry)

            from app.utils.logger import log_interaction

            if sender == "user":
                intent = entry.get("analysis", {}).get("intent", "unknown")
                confidence = entry.get("analysis", {}).get("confidence", 0.0)
                anxiety_score = entry.get("analysis", {}).get("intensity", 0)
                log_interaction(
                    session_id=session_id,
                    user_message=text,
                    intent=intent,
                    confidence=confidence,
                    anxiety_score=anxiety_score,
                    response=response or "",
                    method="session-manager",
                )
            else:
                log_interaction(
                    session_id=session_id,
                    user_message=text,
                    intent=entry.get("analysis", {}).get("intent", ""),
                    confidence=entry.get("analysis", {}).get("confidence", 0.0),
                    anxiety_score=entry.get("analysis", {}).get("anxiety_score", 0),
                    response=response or "",
                    method="session-manager",
                )
    except Exception:
        pass

    _notify_subscribers(session_id, entry)


def get_session(session_id: str):
    return SESSIONS.get(session_id)


def list_active_sessions():
    now = datetime.utcnow()
    result = []
    for s in SESSIONS.values():
        if not s.get("active"):
            continue
        if len(s.get("messages", [])) == 0:
            continue  # never sent a message — likely a stray/incomplete session
        last_msg_time = s["messages"][-1].get("timestamp")
        if last_msg_time:
            try:
                last_dt = datetime.fromisoformat(last_msg_time)
                age_minutes = (now - last_dt).total_seconds() / 60
                if age_minutes > SESSION_STALE_MINUTES:
                    continue  # no activity in 30+ minutes — treat as abandoned
            except (ValueError, TypeError):
                pass
        result.append(s)
    return result


def end_session(session_id: str):
    s = SESSIONS.get(session_id)
    if s:
        s["active"] = False
        s["ended_at"] = datetime.utcnow().isoformat() + "Z"