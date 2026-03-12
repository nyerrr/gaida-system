import json
from datetime import datetime
from pathlib import Path
from app.utils.consent_checker import has_consent

LOG_FILE = Path("logs/interactions.json")


def log_interaction(
    session_id: str,
    user_message: str,
    intent: str,
    confidence: float,
    anxiety_score: int,
    response: str,
    method: str
):
    # 🔐 Ethics check: only log if consent exists
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
        "method": method
    }

    # Load existing logs safely
    if LOG_FILE.exists():
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    # Append new interaction
    data.append(log_entry)

    # Save back to file
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
