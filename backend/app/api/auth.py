import os

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel
from datetime import datetime
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app.database.database import UnconfiguredSupabase, supabase
from app.constants import TEST_CREDENTIALS
from app.services.rate_limiter import check_rate_limit
from app.services.captcha import new_challenge, verify_captcha
from app.services.session_manager import get_session
from app.utils.config import persistence_disabled
from app.utils.auth import create_session_token, get_current_user, revoke_session_token


ALLOWED_DOMAIN = "@ue.edu.ph"

router = APIRouter(prefix="/api/auth", tags=["auth"])


class ForgotPasswordRequest(BaseModel):
    email: str
    role: str = "student"


class LoginRequest(BaseModel):
    student_number: str
    email: str
    access_code: str
    antibot: str
    captcha_token: str = ""


class LoginResponse(BaseModel):
    success: bool
    message: str
    student_id: str = None
    session_token: str = None
    name: str = None


class ConsentRequest(BaseModel):
    session_id: str
    consent_given: bool


class GoogleLoginRequest(BaseModel):
    credential: str
    # NOTE: `role` is only an intent hint ("I clicked the counselor button").
    # It can never grant a role: the issued token's role is derived from the
    # verified email via resolve_google_role(). A counselor intent on an email
    # that is not allowlisted is rejected rather than silently downgraded.
    role: str = "student"


class CounselorLoginRequest(BaseModel):
    faculty_id: str
    password: str
    antibot: str = ""
    captcha_token: str = ""


@router.post("/logout")
def logout(authorization: str = Header(None)):
    """Revoke the current bearer token when a client logs out."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return {"ok": True}
    token = authorization.split(" ", 1)[1].strip()
    if token:
        revoke_session_token(token)
    return {"ok": True}


def _counselor_credentials(faculty_id: str) -> dict | None:
    """Return the counselor account for `faculty_id`, or None.

    Any TEST_CREDENTIALS entry tagged role="counselor" is a valid counselor
    login, so onboarding another counselor is a constants.py change rather than
    a change to this endpoint.
    """
    creds = TEST_CREDENTIALS.get(faculty_id)
    if creds and creds.get("role") == "counselor":
        return creds
    return None


def validate_email_domain(email: str) -> bool:
    return email.strip().lower().endswith(ALLOWED_DOMAIN)


def _counselor_emails() -> set[str]:
    """The emails allowed to receive a counselor role via Google sign-in.

    Counselor identity is derived server-side only. Entries tagged
    role="counselor" in TEST_CREDENTIALS are picked up automatically (when they
    are real @ue.edu.ph addresses), and COUNSELOR_EMAILS — a comma-separated
    env var — lets staff be onboarded without a code change.
    """
    emails = {
        entry.strip().lower()
        for entry in os.getenv("COUNSELOR_EMAILS", "").split(",")
        if entry.strip()
    }
    for creds in TEST_CREDENTIALS.values():
        if creds.get("role") != "counselor":
            continue
        email = str(creds.get("email", "")).strip().lower()
        if email.endswith(ALLOWED_DOMAIN):
            emails.add(email)
    return emails


def resolve_google_role(email: str) -> str:
    """Map a verified Google email to a role. Never trusts the client."""
    return "counselor" if email.strip().lower() in _counselor_emails() else "student"


@router.get("/captcha")
def get_captcha(request: Request, response: Response):
    """Issue a server-drawn verification image + signed single-use token.
    The answer is never sent to the browser; the login endpoints verify it."""
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")
    check_rate_limit(f"captcha:{ip}", limit=60, window=60)
    response.headers["Cache-Control"] = "no-store"
    return new_challenge()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    """
    Authenticate student with temporary test credentials.
    Returns a session token on successful login.
    """
    check_rate_limit(payload.student_number)
    verify_captcha(payload.captcha_token, payload.antibot)

    student_number = payload.student_number.strip()

    email = payload.email.strip().lower()
    if not validate_email_domain(email):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )
    
    credentials = TEST_CREDENTIALS.get(student_number)
    
    if (
        not credentials
        or credentials.get("role") != "student"
        or email != str(credentials.get("email", "")).strip().lower()
        or payload.access_code != credentials.get("access_code")
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    session_token = create_session_token(student_number, role="student")

    return LoginResponse(
        success=True,
        message="Login successful",
        student_id=student_number,
        session_token=session_token,
    )


@router.post("/google", response_model=LoginResponse)
def google_login(payload: GoogleLoginRequest):
    """
    Verify a Google ID token and issue a GAIDA session token.
    Only verified @ue.edu.ph Google accounts are accepted.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured on the server")

    try:
        info = id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            client_id,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google credential")

    if not info.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google email is not verified")

    email = (info.get("email") or "").strip().lower()
    if not validate_email_domain(email):
        raise HTTPException(
            status_code=401,
            detail="Only University of the East (@ue.edu.ph) accounts may sign in",
        )

    check_rate_limit(email)

    # Derive the role from the verified email. The old code used payload.role
    # as the issued role, which let any @ue.edu.ph account mint itself a
    # counselor token. Now the hint can only cause a rejection, never a grant.
    requested_role = (payload.role or "student").strip().lower()
    if requested_role not in ("student", "counselor"):
        raise HTTPException(status_code=400, detail="Invalid role")
    role = resolve_google_role(email)
    if requested_role == "counselor" and role != "counselor":
        raise HTTPException(
            status_code=403,
            detail="This account is not authorized for counselor access",
        )

    user_id = email
    for sid, creds in TEST_CREDENTIALS.items():
        if str(creds.get("email", "")).strip().lower() == email:
            user_id = sid
            break

    session_token = create_session_token(user_id, role=role)

    return LoginResponse(
        success=True,
        message="Login successful",
        student_id=user_id,
        session_token=session_token,
    )


@router.post("/counselor-login", response_model=LoginResponse)
def counselor_login(payload: CounselorLoginRequest):
    """
    Authenticate a guidance counselor. Issues a counselor bearer token that
    unlocks the /api/counselor/* endpoints (role-gated server-side).
    """
    check_rate_limit(payload.faculty_id)
    verify_captcha(payload.captcha_token, payload.antibot)

    faculty_id = payload.faculty_id.strip().upper()
    creds = _counselor_credentials(faculty_id)

    if not creds or payload.password != creds.get("access_code"):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    session_token = create_session_token(faculty_id, role="counselor")

    return LoginResponse(
        success=True,
        message="Login successful",
        student_id=faculty_id,
        session_token=session_token,
        name=creds.get("name"),
    )


@router.post("/consent")
def record_consent(payload: ConsentRequest, user: dict = Depends(get_current_user)):
    """
    Record consent for the authenticated user's session.

    Consent is accepted before the first chat turn, when the client-generated
    session_id does not exist on the server yet. Once a session exists, only
    its owner may change consent for it — otherwise any authenticated user who
    learned another session_id could consent (or revoke consent) on their
    behalf.
    """
    session = get_session(payload.session_id)
    if session and session.get("user_id") and session["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Session does not belong to this user")

    if persistence_disabled() and isinstance(supabase, UnconfiguredSupabase):
        return {
            "success": True,
            "message": f"Consent recorded: {payload.consent_given}",
            "session_id": payload.session_id,
            "stored": False,
        }

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


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest):
    """
    Initiate password reset. Always returns success to prevent email enumeration.
    """
    return {"ok": True, "message": "If the email is registered, a reset link has been sent."}
