import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONSENT_FILE = BASE_DIR / "logs" / "consents.json"


def has_consent(session_id: str) -> bool:
    """
    Check if a session has given consent.
    Returns True only if consent was explicitly recorded.
    """

    if not CONSENT_FILE.exists():
        print(f"DEBUG: Consent file doesn't exist at {CONSENT_FILE}")
        return False

    try:
        with open(CONSENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"DEBUG: Failed to parse consent file")
        return False

    has_it = any(
        entry.get("session_id") == session_id
        and entry.get("consent_given") is True
        for entry in data
    )
    
    print(f"DEBUG: Checking consent for session {session_id}: {has_it}")
    print(f"DEBUG: Consents in file: {[e.get('session_id') for e in data]}")
    
    return has_it
