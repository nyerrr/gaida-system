"""
Research-data-collection endpoints.

Default path is identified: a real student number is captured (same as a
normal login) so returning-student features, follow-up, and counselor
review all work exactly as they do for real sessions. A participant may
instead choose to participate anonymously — in that case no student number
is ever collected, and a signed participant_token is generated and shown to
them once, so they have something to reference later (to withdraw, or to
resume as "the same" pseudonymous person) without it identifying them to
anyone else. The token binds the internal participant id and is verified by
signature, so a raw or tampered code cannot be used to reach someone else's
data. Codes issued before signed tokens still work and are upgraded on the
next start (see _resolve_participant_id).

Demographics (year level, program, gender, region) are captured once per
participant, in research_participants, keyed by participant_id — not once
per session. A returning participant (same student number, or the same
anonymous code entered again) is never asked again; whatever is on file
for them is reused automatically. GAD-7, by contrast, is deliberately
asked every session, since anxiety is expected to vary over time.

Either way, this issues a normal bearer token (see utils/auth.py), so it
works against the existing /virtual-agent and /virtual-agent/stream
endpoints unmodified — no changes needed to the chat pipeline,
session_manager, or the frontend dashboard component.
"""
import re
import secrets
import uuid

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field

from app.database.database import supabase
from app.services.captcha import verify_captcha
from app.services.rate_limiter import check_rate_limit
from app.services.session_manager import start_session, get_session
from app.utils.auth import create_session_token, get_current_user, get_research_access
from app.utils.participant_token import (
    create_participant_token,
    looks_like_participant_token,
    verify_participant_token,
)

router = APIRouter(prefix="/api/research", tags=["research"])


def _client_ip(request: Request) -> str:
    # Deliberately not trusting X-Forwarded-For here: clients can spoof it
    # unless the deployment is known to sit behind a proxy that overwrites it.
    # The CAPTCHA is the primary control; this IP is the rate-limit fallback.
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------------------
# Research access — CAPTCHA-gated intake token
#
# /participant-check, /start, and /withdraw have to work for anonymous
# participants who have no account to log in with. A CAPTCHA-gated, signed,
# short-lived access token gives those endpoints a server-issued credential
# instead of leaving them open to unauthenticated callers.
# ---------------------------------------------------------------------------
RESEARCH_ACCESS_TTL_HOURS = 1


class ResearchAccessRequest(BaseModel):
    captcha_token: str = ""
    antibot: str = ""


class ResearchAccessResponse(BaseModel):
    access_token: str
    expires_in: int


@router.post("/access", response_model=ResearchAccessResponse)
def issue_research_access(payload: ResearchAccessRequest, request: Request):
    """Exchange a solved CAPTCHA for a short-lived research access token."""
    # Generous enough for a class behind one campus NAT; the CAPTCHA is what
    # stops automated token farming, this limit only caps the obvious abuse.
    check_rate_limit(f"research_access:{_client_ip(request)}", limit=100, window=3600)
    verify_captcha(payload.captcha_token, payload.antibot)

    token = create_session_token(
        f"research-access:{uuid.uuid4().hex}",
        role="research_access",
        ttl_hours=RESEARCH_ACCESS_TTL_HOURS,
    )
    return ResearchAccessResponse(
        access_token=token,
        expires_in=int(RESEARCH_ACCESS_TTL_HOURS * 3600),
    )


# ---------------------------------------------------------------------------
# GAD-7 scoring — standard clinical cut-offs (Spitzer et al., 2006)
# ---------------------------------------------------------------------------
def _severity_band(total: int) -> str:
    if total >= 15:
        return "severe"
    if total >= 10:
        return "moderate"
    if total >= 5:
        return "mild"
    return "minimal"


# UE student numbers observed as 4-digit enrollment year + 7-digit sequence
# (11 digits total). Format check only, not verification.
_STUDENT_NUMBER_RE = re.compile(r"^\d{11}$")


def _validate_student_number(value: str) -> None:
    if not _STUDENT_NUMBER_RE.match(value):
        raise HTTPException(
            status_code=400,
            detail="Student number should be 11 digits (e.g. 20240001234).",
        )


def _resolve_participant_id(
    anonymous: bool,
    student_number: str | None,
    participant_code: str | None,
    participant_token: str | None = None,
) -> tuple[str, str | None, bool]:
    """Returns (participant_id, code_used, used_signed_token).

    For the anonymous path, only a signed participant token can resume an
    existing participant. Raw participant codes are not credentials. A
    brand-new anonymous participant gets a fresh code.
    """
    if anonymous:
        credential = (participant_token or "").strip()
        if looks_like_participant_token(credential):
            claims = verify_participant_token(credential)
            if not claims:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Invalid participant token. Check that you pasted the "
                        "full token you saved."
                    ),
                )
            return claims["participant_id"], claims["code"], True

        if credential or (participant_code or "").strip():
            raise HTTPException(status_code=400, detail="A valid participant token is required.")

        code = secrets.token_hex(5)
        return f"anon_{code}", code, False

    if not student_number or not student_number.strip():
        raise HTTPException(
            status_code=400,
            detail="student_number is required unless participating anonymously",
        )
    student_number = student_number.strip()
    _validate_student_number(student_number)
    return student_number, None, False


def _fetch_participant(participant_id: str) -> dict | None:
    result = (
        supabase.table("research_participants")
        .select("year_level, program, gender, region")
        .eq("participant_id", participant_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


# ---------------------------------------------------------------------------
# Check whether a participant is already known, before showing demographics
# ---------------------------------------------------------------------------
class ParticipantCheckRequest(BaseModel):
    anonymous: bool = False
    student_number: str | None = Field(default=None, max_length=50)
    # New client field: the signed token shown once after a first session.
    participant_token: str | None = Field(default=None, max_length=512)
    # Legacy field, kept for participants who joined before signed tokens and
    # for older clients. See _resolve_participant_id.
    participant_code: str | None = Field(default=None, max_length=32)


class ParticipantCheckResponse(BaseModel):
    is_returning: bool


@router.post("/participant-check", response_model=ParticipantCheckResponse)
def check_participant(
    payload: ParticipantCheckRequest,
    request: Request,
    _access: dict = Depends(get_research_access),
):
    """
    Called right after the identification step, before deciding whether to
    show the demographics form. Anonymous participants only get a
    meaningful answer here if they entered a previous code — a brand-new
    anonymous participant has no code yet, so is always "not returning."

    Requires a CAPTCHA-gated research access token (POST /api/research/access).
    This is a boolean "has this student number/code been seen before" check,
    which — without a credential and limit — could be used to mass-enumerate
    which student numbers have used GAIDA (a sensitive fact in a counseling
    context). The per-IP limit remains as a second layer.
    """
    check_rate_limit(f"research_check:{_client_ip(request)}", limit=20, window=60)

    if not payload.anonymous:
        # Student numbers are identifiers, not proof of ownership. Never
        # reveal whether an identified participant has previously enrolled.
        return ParticipantCheckResponse(is_returning=False)

    if not payload.participant_token and not payload.participant_code:
        return ParticipantCheckResponse(is_returning=False)

    participant_id, _, _ = _resolve_participant_id(
        payload.anonymous,
        payload.student_number,
        payload.participant_code,
        payload.participant_token,
    )
    existing = _fetch_participant(participant_id)
    return ParticipantCheckResponse(is_returning=existing is not None)


# ---------------------------------------------------------------------------
# Start a session
# ---------------------------------------------------------------------------
class StartResearchRequest(BaseModel):
    anonymous: bool = False
    student_number: str | None = Field(default=None, max_length=50)
    # Signed token from a previous anonymous session (preferred).
    participant_token: str | None = Field(default=None, max_length=512)
    # Legacy raw code, kept only so pre-token participants can resume.
    participant_code: str | None = Field(default=None, max_length=32)

    # Only used the *first* time a given participant is seen — ignored (not
    # overwritten) for a returning participant, whose stored values are
    # used instead. See _resolve_participant_id / _fetch_participant.
    year_level: str | None = Field(default=None, max_length=50)
    program: str | None = Field(default=None, max_length=100)
    gender: str | None = Field(default=None, max_length=50)
    region: str | None = Field(default=None, max_length=100)


class StartResearchResponse(BaseModel):
    session_token: str
    session_id: str
    participant_id: str
    anonymous: bool
    # Always present for anonymous starts (new, returning, or upgraded from a
    # legacy code). Echoing it lets a returning participant keep using the same
    # deterministic token without the server storing it.
    participant_token: str | None = None
    # True when this client did not send a valid signed token, so it must show
    # the token once and ask the participant to save it.
    participant_token_issued: bool = False


@router.post("/start", response_model=StartResearchResponse)
def start_research_session(
    payload: StartResearchRequest,
    request: Request,
    _access: dict = Depends(get_research_access),
):
    check_rate_limit(f"research_start:{_client_ip(request)}")

    participant_id, code_used, used_signed_token = _resolve_participant_id(
        payload.anonymous,
        payload.student_number,
        payload.participant_code,
        payload.participant_token,
    )

    existing = _fetch_participant(participant_id)
    if existing:
        # Returning participant — always use what's already on file,
        # regardless of what (if anything) this request sent.
        demographics = existing
    else:
        demographics = {
            "year_level": payload.year_level,
            "program": payload.program,
            "gender": payload.gender,
            "region": payload.region,
        }
        try:
            supabase.table("research_participants").insert({
                "participant_id": participant_id,
                "is_anonymous": payload.anonymous,
                **demographics,
            }).execute()
        except Exception as e:
            print(f"[research] participant record creation failed: {e}")

    session_id = str(uuid.uuid4())

    # Reuses the exact same session-creation path real logins use, so the
    # chat pipeline (running confidence, acoustic fusion, returning-student
    # check-ins, etc.) behaves identically for research participants.
    start_session(user_id=participant_id, session_id=session_id)

    try:
        supabase.table("sessions").update({
            "is_research": True,
            "is_anonymous": payload.anonymous,
            "participant_code": code_used,  # None for identified participants
            **demographics,
        }).eq("session_token", session_id).execute()
    except Exception as e:
        # Non-fatal — the session still works for chat even if this tagging
        # update fails; it just won't be picked up by the export script.
        print(f"[research] session tagging failed: {e}")

    token = create_session_token(participant_id, role="research")

    participant_token = None
    participant_token_issued = False
    if payload.anonymous:
        participant_token = create_participant_token(participant_id)
        # A new participant, or one arriving with a pre-token legacy code, has
        # not sent a signed token yet and must save this one. A returning
        # participant who already sent one gets the same deterministic token
        # back and is not asked to save it again.
        participant_token_issued = not used_signed_token

    return StartResearchResponse(
        session_token=token,
        session_id=session_id,
        participant_id=participant_id,
        anonymous=payload.anonymous,
        participant_token=participant_token,
        participant_token_issued=participant_token_issued,
    )


# ---------------------------------------------------------------------------
# GAD-7 — deliberately asked every session, not gated by participant history
# ---------------------------------------------------------------------------
class Gad7Request(BaseModel):
    session_id: str
    answers: list[int] = Field(min_length=7, max_length=7)


class Gad7Response(BaseModel):
    total_score: int
    severity_band: str


# ---------------------------------------------------------------------------
# Withdraw — delete all data tied to an anonymous participant
# (This is the "delete my data" promise the research consent makes; a signed
# participant token is required to identify the participant.)
# ---------------------------------------------------------------------------
class WithdrawRequest(BaseModel):
    # Preferred: the signed participant token.
    participant_token: str | None = Field(default=None, max_length=512)
    # Deprecated compatibility field. Values here are rejected; a raw code
    # is guessable and cannot authorize access to another participant's data.
    participant_code: str | None = Field(default=None, max_length=32)


class WithdrawResponse(BaseModel):
    ok: bool
    deleted_sessions: int = 0
    participant_removed: bool = False
    errors: list[str] = []


# Every child table is keyed by the same session_id string used across the
# app, so deleting is a simple multi-table sweep in session_id order.
# Keep in sync with CHILD_TABLES in tools/delete_participant.py.
_WITHDRAW_SESSION_CHILD_TABLES = [
    "interactions",
    "consents",
    "gad7_responses",
    "sus_responses",
    "message_feedback",
    "session_ratings",
    "session_notes",
    "counselor_alerts",
    "acoustic_logs",
]


@router.post("/withdraw", response_model=WithdrawResponse)
def withdraw_anonymous_code(
    payload: WithdrawRequest,
    request: Request,
    _access: dict = Depends(get_research_access),
):
    """
    Irreversibly delete every record tied to an anonymous participant code:
    sessions, chat interactions, GAD-7 responses, ratings, notes, alerts,
    acoustic logs, and the participant row itself. Idempotent — submitting an
    unknown code safely returns an empty "everything deleted" result.

    Requires a CAPTCHA-gated research access token (POST /api/research/access),
    so the destructive lookup is not reachable by an unauthenticated script.
    A signed participant token is required. Raw codes are not accepted because
    they are enumerable and do not prove control of a participant credential.
    """
    # Stricter than the default 5/min: this endpoint hard-deletes data on a
    # single credential, so brute-forcing or mass-triggering it needs to be far
    # more expensive than a login attempt. 3/hour/IP still comfortably covers a
    # genuine participant withdrawing (once) while making enumeration
    # impractical.
    check_rate_limit(f"research_withdraw:{_client_ip(request)}", limit=3, window=3600)

    if not (payload.participant_token or payload.participant_code):
        raise HTTPException(status_code=400, detail="A participant token is required.")

    participant_id, code, _ = _resolve_participant_id(
        anonymous=True,
        student_number=None,
        participant_code=payload.participant_code,
        participant_token=payload.participant_token,
    )
    errors: list[str] = []

    # 1. Find every session that belongs to this code.
    try:
        sessions = (
            supabase.table("sessions")
            .select("session_token")
            .eq("participant_code", code)
            .execute()
        )
        session_ids = [row["session_token"] for row in (sessions.data or [])]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to look up sessions: {e}")

    # 2. Delete session-scoped child rows. A table can be absent in some
    # Supabase setups; do not fail the whole withdrawal because of one
    # missing/renamed table, but do report it — a silent skip here would
    # leave data behind while telling the participant everything was gone.
    if session_ids:
        for table in _WITHDRAW_SESSION_CHILD_TABLES:
            try:
                supabase.table(table).delete().in_("session_id", session_ids).execute()
            except Exception as e:
                print(f"[research] withdraw: {table} sweep failed: {e}")
                errors.append(f"{table}: {e}")

    # 3. Delete the session rows themselves.
    try:
        supabase.table("sessions").delete().eq("participant_code", code).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete sessions: {e}")

    # 4. Delete the participant row. Check whether it existed first, so an
    # already-absent row (nothing to delete) isn't mistaken for a failed
    # delete — and so a real delete failure is never silently swallowed
    # into a false "ok: true" the way it used to be.
    participant_existed = False
    try:
        existing = (
            supabase.table("research_participants")
            .select("participant_id")
            .eq("participant_id", participant_id)
            .limit(1)
            .execute()
        )
        participant_existed = bool(existing.data)
    except Exception as e:
        print(f"[research] withdraw: participant lookup failed: {e}")
        errors.append(f"research_participants lookup: {e}")

    participant_removed = not participant_existed
    if participant_existed:
        try:
            result = (
                supabase.table("research_participants")
                .delete()
                .eq("participant_id", participant_id)
                .execute()
            )
            participant_removed = bool(result.data)
            if not participant_removed:
                errors.append("research_participants: delete returned no rows")
        except Exception as e:
            print(f"[research] withdraw: participant row delete failed: {e}")
            errors.append(f"research_participants delete: {e}")

    return WithdrawResponse(
        ok=len(errors) == 0,
        deleted_sessions=len(session_ids),
        participant_removed=participant_removed,
        errors=errors,
    )


@router.post("/gad7", response_model=Gad7Response)
def submit_gad7(payload: Gad7Request, user: dict = Depends(get_current_user)):
    if any(a < 0 or a > 3 for a in payload.answers):
        raise HTTPException(status_code=400, detail="Each answer must be between 0 and 3")

    session = get_session(payload.session_id)
    if session and session.get("user_id") and session["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Session does not belong to this user")

    total = sum(payload.answers)
    band = _severity_band(total)

    try:
        supabase.table("gad7_responses").insert({
            "session_id": payload.session_id,
            "q1": payload.answers[0], "q2": payload.answers[1],
            "q3": payload.answers[2], "q4": payload.answers[3],
            "q5": payload.answers[4], "q6": payload.answers[5],
            "q7": payload.answers[6],
            "total_score": total,
            "severity_band": band,
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store GAD-7 response: {e}")

    return Gad7Response(total_score=total, severity_band=band)


class SusRequest(BaseModel):
    session_id: str
    # 10 answers, each 1-5, in SUS question order (see frontend
    # ResearchSUS.jsx for the exact wording shown to participants).
    answers: list[int] = Field(min_length=10, max_length=10)
    comment: str = Field(default="", max_length=1000)


class SusResponse(BaseModel):
    sus_score: float


def _sus_score(answers: list[int]) -> float:
    """
    Standard SUS scoring (Brooke, 1996).
    Odd items (index 0,2,4,6,8 -> q1,q3,q5,q7,q9): score = answer - 1.
    Even items (index 1,3,5,7,9 -> q2,q4,q6,q8,q10): score = 5 - answer.
    Sum the 10 per-item scores (range 0-40) and multiply by 2.5 -> 0-100.
    """
    total = 0
    for i, a in enumerate(answers):
        total += (a - 1) if i % 2 == 0 else (5 - a)
    return round(total * 2.5, 2)


@router.post("/sus", response_model=SusResponse)
def submit_sus(payload: SusRequest, user: dict = Depends(get_current_user)):
    """
    Store one System Usability Scale administration for a research session.
    Reached after the participant's chat session ends (see ResearchSUS.jsx),
    not during intake — SUS measures usability of a system just used, so it
    has to come after the participant has actually used GAIDA. Requires the
    session_token confirmEndSession deliberately keeps around for research
    sessions until this page clears it — same auth pattern as /gad7.
    """
    if any(a < 1 or a > 5 for a in payload.answers):
        raise HTTPException(status_code=400, detail="Each answer must be between 1 and 5")

    session = get_session(payload.session_id)
    if session and session.get("user_id") and session["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Session does not belong to this user")

    score = _sus_score(payload.answers)
    comment = payload.comment.strip()

    try:
        supabase.table("sus_responses").insert({
            "session_id": payload.session_id,
            "q1": payload.answers[0], "q2": payload.answers[1],
            "q3": payload.answers[2], "q4": payload.answers[3],
            "q5": payload.answers[4], "q6": payload.answers[5],
            "q7": payload.answers[6], "q8": payload.answers[7],
            "q9": payload.answers[8], "q10": payload.answers[9],
            "sus_score": score,
            "comment": comment or None,
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store SUS response: {e}")

    return SusResponse(sus_score=score)
