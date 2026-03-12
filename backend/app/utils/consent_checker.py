import json
from pathlib import Path

CONSENT_FILE = Path("logs/consents.json")


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
