import json
from pathlib import Path
from datetime import datetime

CONSENT_FILE = Path("logs/consents.json")


def _load_consents() -> list:
    if not CONSENT_FILE.exists():
        return []
    try:
        with open(CONSENT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []


def _save_consents(data: list):
    CONSENT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONSENT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def log_consent(session_id: str, consent_given: bool):
    """
    Insert or update a consent record for a session.
    - First time: sets both recorded_at and updated_at
    - Subsequent calls: only updates consent_given and updated_at
    """
    data = _load_consents()
    now = datetime.now().isoformat()

    # Check if session already exists
    for entry in data:
        if entry.get("session_id") == session_id:
            entry["consent_given"] = consent_given
            entry["updated_at"] = now
            _save_consents(data)
            return

    # New entry
    data.append({
        "session_id": session_id,
        "consent_given": consent_given,
        "recorded_at": now,
        "updated_at": now
    })
    _save_consents(data)


def has_consent(session_id: str) -> bool:
    """
    Check if a session has given consent.
    Returns True only if consent was explicitly recorded.
    """
    if not CONSENT_FILE.exists():
        return False
    try:
        with open(CONSENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return False

    return any(
        entry.get("session_id") == session_id
        and entry.get("consent_given") is True
        for entry in data
    )