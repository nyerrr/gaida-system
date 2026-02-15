from typing import Dict, Any, List, Callable
from datetime import datetime
import uuid
import json
from pathlib import Path
import asyncio

from app.utils.consent_checker import has_consent

SESSIONS: Dict[str, Dict[str, Any]] = {}
_SUBSCRIBERS: List[Callable] = []

LOG_FILE = Path("logs/interactions.json")


def start_session(user_id: str | None = None) -> str:
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {
        "session_id": session_id,
        "user_id": user_id,
        "started_at": datetime.utcnow().isoformat(),
        "messages": [],
        "active": True,
        "meta": {}
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
        if LOG_FILE.exists():
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []
    except Exception:
        data = []

    data.append(entry)

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def record_interaction(session_id: str, sender: str, text: str, analysis: Dict | None = None, response: str | None = None):
    session = SESSIONS.get(session_id)
    if session is None:
        # create ephemeral session if missing
        session_id = start_session(None)
        session = SESSIONS[session_id]

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
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

    # Persist only if consent exists for this session
    try:
        if has_consent(session_id):
            _persist_entry(entry)
    except Exception:
        # if consent check fails, skip persistence
        pass

    # Notify subscribers (e.g., WebSocket manager)
    _notify_subscribers(session_id, entry)


def get_session(session_id: str):
    return SESSIONS.get(session_id)


def list_active_sessions():
    return [s for s in SESSIONS.values() if s.get("active")]


def end_session(session_id: str):
    s = SESSIONS.get(session_id)
    if s:
        s["active"] = False
        s["ended_at"] = datetime.utcnow().isoformat()
