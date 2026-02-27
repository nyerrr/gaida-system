import json
from datetime import datetime
from pathlib import Path
from app.utils.consent_checker import has_consent

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_FILE = BASE_DIR / "logs" / "interactions.json"


def log_interaction(
    session_id: str,
    user_message: str,
    intent: str,
    confidence: float,
    anxiety_score: int,
    response: str,
    method: str
):

    if not has_consent(session_id):
        return

    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": session_id,
        "user_message": user_message,
        "intent": intent,
        "confidence": confidence,
        "anxiety_score": anxiety_score,
        "response": response,
        "method": method,
    }

    # Load safely
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []
    else:
        data = []

    data.append(log_entry)

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)