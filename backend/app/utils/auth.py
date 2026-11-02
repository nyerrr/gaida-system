import base64
import hashlib
import hmac
import json
import os
from secrets import token_urlsafe
from time import time

from fastapi import Depends, Header, HTTPException

# In-memory token store: token -> { user_id, role, expires_at }
#
# Tokens survive a server restart when AUTH_SECRET is set: the token itself then
# carries {user, role, expiry} and an HMAC signature, so validate_token() can
# rebuild the record after a restart or a Replit wake-up instead of signing
# every student out mid-chat. Without AUTH_SECRET this behaves exactly as
# before (tokens live only in memory). Changing AUTH_SECRET signs everyone out.
ACTIVE_TOKENS = {}
# Logged-out signed tokens. In memory only, so a restart forgets them; a token
# revoked this way can then work again until its 12 hour expiry.
REVOKED_TOKENS = set()

TOKEN_TTL_HOURS = 12


def _secret() -> bytes:
    return os.getenv("AUTH_SECRET", "").encode("utf-8")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _signature(body: str) -> str:
    return _b64(hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest())


def create_session_token(user_id: str, role: str = "student") -> str:
    """Issue a bearer token for the given user and store it in ACTIVE_TOKENS."""
    expires_at = time() + TOKEN_TTL_HOURS * 3600
    if _secret():
        body = _b64(json.dumps(
            {"u": user_id, "r": role, "e": int(expires_at), "n": token_urlsafe(6)},
            separators=(",", ":"),
        ).encode("utf-8"))
        token = f"token_{role}_{body}.{_signature(body)}"
    else:
        token = f"token_{role}_{token_urlsafe(16)}"
    ACTIVE_TOKENS[token] = {
        "user_id": user_id,
        "role": role,
        "expires_at": expires_at,
    }
    return token


def revoke_session_token(token: str):
    """Invalidate a token immediately (e.g. logout)."""
    ACTIVE_TOKENS.pop(token, None)
    if _secret() and "." in token:
        if len(REVOKED_TOKENS) > 5000:
            REVOKED_TOKENS.clear()
        REVOKED_TOKENS.add(token)


def _purge_expired():
    now = time()
    for token in list(ACTIVE_TOKENS):
        if ACTIVE_TOKENS[token].get("expires_at", 0) < now:
            del ACTIVE_TOKENS[token]


def get_current_user(authorization: str = Header(None)) -> dict:
    """FastAPI dependency — validates `Authorization: Bearer <token>`.

    Returns the authenticated user dict {user_id, role, expires_at}
    or raises 401.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")

    user = validate_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    return user


def require_role(*roles: str):
    """Dependency factory: require the authenticated user to hold one of `roles`.

    Usage: `user: dict = Depends(require_role("counselor"))`
    """
    def _dependency(user: dict = Depends(get_current_user)):
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return _dependency


def validate_token(token: str) -> dict | None:
    """Return the user record for a raw token, or None if invalid/expired.

    Used for WebSocket handshakes (query param) where Header() deps
    aren't available.
    """
    if not token:
        return None
    _purge_expired()
    record = ACTIVE_TOKENS.get(token)
    if record:
        return record
    return _restore_signed_token(token)


def _restore_signed_token(token: str) -> dict | None:
    """Rebuild a token record from its signature (server restarted)."""
    if not _secret() or token in REVOKED_TOKENS:
        return None
    try:
        prefix, sig = token.rsplit(".", 1)
        body = prefix.rsplit("_", 1)[1]
        if not hmac.compare_digest(sig, _signature(body)):
            return None
        data = json.loads(_unb64(body))
        expires_at = float(data["e"])
        if expires_at < time():
            return None
        role = str(data["r"])
        if not prefix.startswith(f"token_{role}_"):
            return None
        record = {"user_id": str(data["u"]), "role": role, "expires_at": expires_at}
    except (ValueError, KeyError, IndexError, TypeError):
        return None
    ACTIVE_TOKENS[token] = record
    return record
