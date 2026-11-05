"""Research intake and withdrawal endpoints require a server-issued token.

Anonymous participants have no account, so the public research endpoints are
gated by a short-lived token issued only after a CAPTCHA challenge. These tests
pin that contract: no token (or a normal student token) gets 401, a valid
CAPTCHA buys an access token, and that token cannot be replayed against the
normal chat/session API.
"""

import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

pytest.importorskip("fastapi")

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api import research
from app.main import app
from app.services import captcha, rate_limiter
from app.utils import auth
from app.utils.auth import create_session_token


@pytest.fixture(autouse=True)
def _clean_state():
    rate_limiter.users_requests.clear()
    auth.ACTIVE_TOKENS.clear()
    auth.REVOKED_TOKENS.clear()
    yield
    rate_limiter.users_requests.clear()
    auth.ACTIVE_TOKENS.clear()
    auth.REVOKED_TOKENS.clear()


@pytest.fixture()
def client():
    return TestClient(app)


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _captcha_token(answer: str = "ABCDEF") -> str:
    nonce = "research-test-" + str(time.time_ns())
    exp = int(time.time()) + 60
    return f"{nonce}.{exp}.{captcha._sign(nonce, exp, answer)}"


def _access(client, answer: str = "ABCDEF") -> str:
    r = client.post(
        "/api/research/access",
        json={"captcha_token": _captcha_token(answer), "antibot": answer},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_access_requires_a_captcha(client):
    r = client.post("/api/research/access", json={})

    assert r.status_code == 400


def test_access_rejects_a_consumed_captcha(client):
    token = _captcha_token()
    body = {"captcha_token": token, "antibot": "ABCDEF"}

    assert client.post("/api/research/access", json=body).status_code == 200
    assert client.post("/api/research/access", json=body).status_code == 400


def test_participant_check_requires_access_token(client):
    r = client.post(
        "/api/research/participant-check",
        json={"anonymous": False, "student_number": "20240001234"},
    )

    assert r.status_code == 401


def test_participant_check_rejects_a_normal_student_token(client):
    token = create_session_token("2024001", role="student")

    r = client.post(
        "/api/research/participant-check",
        json={"anonymous": False, "student_number": "20240001234"},
        headers=_headers(token),
    )

    assert r.status_code == 401


def test_start_requires_access_token(client):
    r = client.post(
        "/api/research/start",
        json={"anonymous": True},
    )

    assert r.status_code == 401


def test_withdraw_requires_access_token(client):
    r = client.post(
        "/api/research/withdraw",
        json={"participant_code": "abc123"},
    )

    assert r.status_code == 401


def test_withdraw_rejects_a_normal_student_token(client):
    token = create_session_token("2024001", role="student")

    r = client.post(
        "/api/research/withdraw",
        json={"participant_code": "abc123"},
        headers=_headers(token),
    )

    assert r.status_code == 401


def test_valid_access_token_unlocks_participant_check(client, monkeypatch):
    monkeypatch.setattr(research, "_fetch_participant", lambda _participant_id: None)
    access = _access(client)

    r = client.post(
        "/api/research/participant-check",
        json={"anonymous": False, "student_number": "20240001234"},
        headers=_headers(access),
    )

    assert r.status_code == 200, r.text
    assert r.json() == {"is_returning": False}


def test_access_token_cannot_be_used_as_a_normal_session(client):
    access = _access(client)

    r = client.post("/api/session/start", json={}, headers=_headers(access))

    assert r.status_code == 401


def test_access_token_validation_helpers():
    access = create_session_token("research-access:test", role="research_access", ttl_hours=1)

    assert auth.get_research_access(f"Bearer {access}")["role"] == "research_access"
    with pytest.raises(HTTPException):
        auth.get_current_user(f"Bearer {access}")

    student = create_session_token("2024001", role="student")
    with pytest.raises(HTTPException):
        auth.get_research_access(f"Bearer {student}")
