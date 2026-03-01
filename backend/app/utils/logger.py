import json
import logging
from datetime import datetime
from pathlib import Path
from app.utils.consent_checker import has_consent

# Configure structured logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create logs directory if it doesn't exist
BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "interactions.json"
LOG_DEBUG_FILE = LOG_DIR / "debug.log"

# File handler for debug logs
if not logger.handlers:
    fh = logging.FileHandler(LOG_DEBUG_FILE)
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    fh.setFormatter(formatter)
    logger.addHandler(fh)


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