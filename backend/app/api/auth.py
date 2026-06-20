from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from app.database.database import supabase

ALLOWED_DOMAIN = "@ue.edu.ph"

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Temporary test credentials for development/testing
TEST_CREDENTIALS = {
    "2024001": {
        "email": "student1@ue.edu.ph",
        "access_code": "ACCESS123",
    },
    "2024002": {
        "email": "student2@ue.edu.ph",
        "access_code": "ACCESS456",
    },
    "2024003": {
        "email": "student3@ue.edu.ph",
        "access_code": "ACCESS789",
    },
    "COUNSELOR01": {
        "email": "counselor@ue.edu.ph",
        "access_code": "COUNSEL123",
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


def validate_email_domain(email: str) -> bool:
    return email.strip().lower().endswith(ALLOWED_DOMAIN)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    """
    Authenticate student with temporary test credentials.
    Returns a session token on successful login.
    """
    student_number = payload.student_number.strip()

    if not validate_email_domain(payload.email):
        raise HTTPException(
            status_code=400,
            detail=f"Email must end with {ALLOWED_DOMAIN}"
        )
    
    # Check if student number exists in test credentials
    if student_number not in TEST_CREDENTIALS:
        raise HTTPException(status_code=401, detail="Invalid student number")
    
    credentials = TEST_CREDENTIALS[student_number]
    
    # Validate credentials (antibot is verified client-side via canvas captcha)
    if (payload.email != credentials["email"] or
        payload.access_code != credentials["access_code"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate a simple session token (in production, use JWT)
    session_token = f"token_{student_number}_{int(__import__('time').time())}"
    supabase.table("sessions").insert({
        "student_id": student_number,
        "session_token": session_token,
        "is_counselor": student_number.startswith("COUNSELOR")
    }).execute()

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
    existing = supabase.table("consents")\
        .select("*")\
        .eq("session_id", payload.session_id)\
        .execute()
    
    if existing.data:
        supabase.table("consents")\
            .update({
                "consent_given": payload.consent_given,
                "updated_at": datetime.utcnow().isoformat()
            })\
            .eq("session_id", payload.session_id)\
            .execute()
    else:
        supabase.table("consents")\
            .insert({
                "session_id": payload.session_id,
                "consent_given": payload.consent_given,
            })\
            .execute()
    return {
        "success": True,
        "message": f"Consent recorded: {payload.consent_given}",
        "session_id": payload.session_id,
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
            {
                "email": "counselor@ue.edu.ph",
                "access_code": "COUNSEL123",
                "antibot": "GAIDA",
            }
        ]
    }
