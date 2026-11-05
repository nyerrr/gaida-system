"""Signed participant tokens for anonymous research participants.

An anonymous participant has no account, so the credential they save is the
only way to resume as the same pseudonymous person or to withdraw their data.
That credential used to be a plain random code the server looked up in the
database, which meant any guessed code that matched a row was accepted.

A participant token is the same identity, signed by the server:

    pt1_<base64url({"p": "anon_<code>"})>.<hmac-sha256>

The payload carries only the internal participant id; the short code is the
part after ``anon_``. A raw code, a modified payload, or a token signed with a
different key is rejected before any database lookup happens.

Tokens deliberately do not expire: the consent text promises a participant can
come back and withdraw at any time, and stored research data already has a
fixed retention period. Verification is stateless — no database row or
in-memory table is needed.

The signing key is ``PARTICIPANT_TOKEN_SECRET``, falling back to ``AUTH_SECRET``.
If neither is set, a random per-process key is generated so local development
and tests still work, but tokens then stop working after a restart. Set one of
them in any real deployment.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets

TOKEN_PREFIX = "pt1_"
_ANON_PREFIX = "anon_"
_MAX_TOKEN_LENGTH = 512

# Used only when neither environment variable is configured. Generating a new
# value on each process start is what makes unconfigured tokens short-lived.
_FALLBACK_SECRET = secrets.token_hex(32)


def _secret() -> bytes:
    return (
        os.getenv("PARTICIPANT_TOKEN_SECRET")
        or os.getenv("AUTH_SECRET")
        or _FALLBACK_SECRET
    ).encode("utf-8")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _signature(body: str) -> str:
    return _b64(
        hmac.new(
            _secret(),
            f"{TOKEN_PREFIX}{body}".encode("ascii"),
            hashlib.sha256,
        ).digest()
    )


def create_participant_token(participant_id: str) -> str:
    """Return a signed token for an anonymous participant id."""
    participant_id = (participant_id or "").strip()
    if not participant_id.startswith(_ANON_PREFIX) or participant_id == _ANON_PREFIX:
        raise ValueError("participant_id must be an anonymous participant id")

    payload = json.dumps({"p": participant_id}, separators=(",", ":")).encode("utf-8")
    body = _b64(payload)
    return f"{TOKEN_PREFIX}{body}.{_signature(body)}"


def verify_participant_token(token: str | None) -> dict | None:
    """Return ``{"participant_id", "code"}`` for a valid token, else None.

    Never raises for malformed input: callers turn None into a 400.
    """
    if not token or len(token) > _MAX_TOKEN_LENGTH or not token.startswith(TOKEN_PREFIX):
        return None

    try:
        body, signature = token[len(TOKEN_PREFIX):].rsplit(".", 1)
        if not hmac.compare_digest(signature, _signature(body)):
            return None
        data = json.loads(_unb64(body))
        participant_id = str(data["p"])
    except (ValueError, KeyError, TypeError):
        return None

    if not participant_id.startswith(_ANON_PREFIX) or participant_id == _ANON_PREFIX:
        return None
    return {
        "participant_id": participant_id,
        "code": participant_id[len(_ANON_PREFIX):],
    }


def looks_like_participant_token(value: str | None) -> bool:
    """True when *value* is meant to be a signed token rather than a legacy code."""
    return bool(value) and value.startswith(TOKEN_PREFIX)
