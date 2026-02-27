from typing import Dict, Any, List, Callable
from datetime import datetime
import uuid
import json
from pathlib import Path
import asyncio

from app.utils.consent_checker import has_consent

SESSIONS: Dict[str, Dict[str, Any]] = {}
_SUBSCRIBERS: List[Callable] = []

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_FILE = BASE_DIR / "logs" / "interactions.json"


def start_session(user_id: str | None = None, session_id: str | None = None) -> str:
    """Create a new session record.

    If ``session_id`` is provided we use it verbatim; otherwise we generate a
    fresh UUID.  This guarantees that callers who already know their ID
    (e.g. ``analyze_intent``) will not have it silently replaced by a random
    value later in ``record_interaction``.
    """

    if session_id is None:
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
        # create ephemeral session if missing.  respect any ID the caller
        # supplied so that all interactions in a single conversation use the
        # same identifier.
        session_id = start_session(None, session_id=session_id)
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

            # also mirror the interaction into the flattened log format
            # used by ``log_interaction`` so that every message contains
            # session_id, intent/confidence, etc.  when the message comes
            # from the user we have analysis info already; for bot replies
            # we synthesize whatever metadata we can.
            from app.utils.logger import log_interaction

            if sender == "user":
                # user message is the primary thing we care about
                intent = entry.get("analysis", {}).get("intent", "unknown")
                confidence = entry.get("analysis", {}).get("confidence", 0.0)
                anxiety_score = entry.get("analysis", {}).get(
                    "intensity", 0
                )
                # response field is kept empty for user inputs
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
                # bot replies can also be logged if desired (optional)
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
