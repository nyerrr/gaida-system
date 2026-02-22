from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
from pathlib import Path
from datetime import datetime

router = APIRouter(prefix="/api/auth", tags=["auth"])
CONSENT_FILE = Path("logs/consents.json")

# Temporary test credentials for development/testing
TEST_CREDENTIALS = {
    "2024001": {
        "email": "student1@ue.edu.ph",
        "access_code": "ACCESS123",
        "antibot": "HELLO",
    },
    "2024002": {
        "email": "student2@ue.edu.ph",
        "access_code": "ACCESS456",
        "antibot": "WORLD",
    },
    "2024003": {
        "email": "student3@ue.edu.ph",
        "access_code": "ACCESS789",
        "antibot": "GAIDA",
    },
    "COUNSELOR01": {
        "email": "counselor@ue.edu.ph",
        "access_code": "COUNSEL123",
        "antibot": "GAIDA",
    },
}


class LoginRequest(BaseModel):
    student_number: str
    email: str
    access_code: str
    antibot: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    student_id: str = None
    session_token: str = None


class ConsentRequest(BaseModel):
    session_id: str
    consent_given: bool


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    """
    Authenticate student with temporary test credentials.
    Returns a session token on successful login.
    """
    student_number = payload.student_number.strip()
    
    # Check if student number exists in test credentials
    if student_number not in TEST_CREDENTIALS:
        raise HTTPException(status_code=401, detail="Invalid student number")
    
    credentials = TEST_CREDENTIALS[student_number]
    
    # Validate all fields
    if (payload.email != credentials["email"] or
        payload.access_code != credentials["access_code"] or
        payload.antibot != credentials["antibot"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate a simple session token (in production, use JWT)
    session_token = f"token_{student_number}_{int(__import__('time').time())}"
    
    return LoginResponse(
        success=True,
        message="Login successful",
        student_id=student_number,
        session_token=session_token,
    )


@router.post("/consent")
def record_consent(payload: ConsentRequest):
    """
    Record user consent for logging interactions.
    """
    # Load existing consents
    if CONSENT_FILE.exists():
        with open(CONSENT_FILE, "r", encoding="utf-8") as f:
            consents = json.load(f)
    else:
        consents = []
    
    # Check if session already has consent recorded
    existing = next((c for c in consents if c.get("session_id") == payload.session_id), None)
    
    if existing:
        existing["consent_given"] = payload.consent_given
        existing["updated_at"] = datetime.utcnow().isoformat()
    else:
        consents.append({
            "session_id": payload.session_id,
            "consent_given": payload.consent_given,
            "recorded_at": datetime.utcnow().isoformat()
        })
    
    # Save consents
    CONSENT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONSENT_FILE, "w", encoding="utf-8") as f:
        json.dump(consents, f, indent=2)
    
    return {
        "success": True,
        "message": f"Consent recorded: {payload.consent_given}",
        "session_id": payload.session_id
    }


@router.get("/test-credentials")
def get_test_credentials():
    """
    Get available test credentials for development/testing.
    REMOVE THIS ENDPOINT IN PRODUCTION!
    """
    return {
        "test_accounts": [
            {
                "student_number": "2024001",
                "email": "student1@ue.edu.ph",
                "access_code": "ACCESS123",
                "antibot": "HELLO",
            },
            {
                "student_number": "2024002",
                "email": "student2@ue.edu.ph",
                "access_code": "ACCESS456",
                "antibot": "WORLD",
            },
            {
                "student_number": "2024003",
                "email": "student3@ue.edu.ph",
                "access_code": "ACCESS789",
                "antibot": "GAIDA",
            },
        ]
    }
