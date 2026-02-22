from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/counselor", tags=["counselor"])


# ---------------------------------------------------------------------------
# Severity mapping
# Converts anxiety_score (int) to Low / Moderate / High label.
# Scores come from anxiety_scoring.py:
#   0 = faq / neutral
#   1 = unknown / other
#   3 = stress / sadness
#   5 = anxiety / suicidal
# ---------------------------------------------------------------------------

SEVERITY_MAP = {
    0: "Low",
    1: "Low",
    3: "Moderate",
    5: "High",
}


def get_severity(anxiety_score: int) -> str:
    """Return Low, Moderate, or High based on anxiety_score."""
    return SEVERITY_MAP.get(anxiety_score, "Low")


def should_alert_counselor(severity: str) -> bool:
    """Return True if severity warrants a counselor alert."""
    return severity == "High"


# ---------------------------------------------------------------------------
# In-memory alert store (replace with DB in production)
# ---------------------------------------------------------------------------

ALERTS: list[dict] = []


# ---------------------------------------------------------------------------
# Internal function called by intent_router.py (not an API endpoint)
# ---------------------------------------------------------------------------

def process_alert(
    session_id: str,
    user_id: Optional[str],
    intent: str,
    anxiety_score: int,
    message: str,
) -> dict:
    """
    Maps anxiety_score to severity.
    Logs an alert if severity is High.
    Returns a dict with severity and alert status.
    """
    severity = get_severity(anxiety_score)
    alert_sent = False

    if should_alert_counselor(severity):
        alert_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "user_id": user_id,
            "intent": intent,
            "anxiety_score": anxiety_score,
            "severity": severity,
            "message": message,
            "status": "pending",
        }
        ALERTS.append(alert_entry)
        alert_sent = True

    return {
        "severity": severity,
        "alert_sent": alert_sent,
    }


# ---------------------------------------------------------------------------
# API endpoints for counselor dashboard
# ---------------------------------------------------------------------------

class AlertStatusUpdate(BaseModel):
    session_id: str
    status: str  # "reviewed", "resolved", "escalated"


@router.get("/alerts")
def get_alerts():
    """Return all counselor alerts. Counselor dashboard calls this."""
    return {"alerts": ALERTS}


@router.get("/alerts/pending")
def get_pending_alerts():
    """Return only unreviewed High severity alerts."""
    pending = [a for a in ALERTS if a.get("status") == "pending"]
    return {"alerts": pending, "count": len(pending)}


@router.post("/alerts/update")
def update_alert_status(payload: AlertStatusUpdate):
    """Counselor marks an alert as reviewed, resolved, or escalated."""
    for alert in ALERTS:
        if alert["session_id"] == payload.session_id:
            alert["status"] = payload.status
            alert["updated_at"] = datetime.utcnow().isoformat()
            return {"ok": True, "session_id": payload.session_id, "status": payload.status}
    return {"ok": False, "error": "Alert not found"}


@router.get("/severity/{anxiety_score}")
def check_severity(anxiety_score: int):
    """Utility endpoint to check what severity a score maps to."""
    severity = get_severity(anxiety_score)
    return {
        "anxiety_score": anxiety_score,
        "severity": severity,
        "requires_alert": should_alert_counselor(severity),
    }