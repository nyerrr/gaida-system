import json
from datetime import datetime
from pathlib import Path

LOG_FILE = Path("logs/interactions.json")

def log_interaction(
    user_message: str,
    intent: str,
    confidence: float,
    response: str,
    method: str
):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_message": user_message,
        "intent": intent,
        "confidence": confidence,
        "response": response,
        "method": method
    }

    # Load existing logs
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
