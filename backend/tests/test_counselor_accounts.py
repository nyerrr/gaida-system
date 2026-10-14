"""Counselor accounts and multi-counselor login.

Counselor login used to accept exactly one hardcoded account (COUNSELOR01).
It now accepts any TEST_CREDENTIALS entry tagged role="counselor", so
onboarding another counselor is a constants.py change, not an auth.py change.
These tests pin that contract so it cannot quietly regress to a single account.
"""

import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app.constants import TEST_CREDENTIALS
from app.services import captcha as captcha_service
from app.utils.auth import ACTIVE_TOKENS


def _client():
    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app)


def _captcha_token(answer: str = "HELLO") -> str:
    nonce = "tok" + str(time.time_ns())
    exp = int(time.time()) + 300
    return f"{nonce}.{exp}.{captcha_service._sign(nonce, exp, answer)}"


def _counselors() -> dict:
    return {
        sid: creds
        for sid, creds in TEST_CREDENTIALS.items()
        if creds.get("role") == "counselor"
    }


def test_five_counselor_accounts_are_configured():
    assert len(_counselors()) == 5


@pytest.mark.parametrize("faculty_id", list(_counselors()))
def test_each_counselor_can_log_in_and_gets_a_counselor_token(faculty_id):
    creds = TEST_CREDENTIALS[faculty_id]
    r = _client().post(
        "/api/auth/counselor-login",
        json={
            "faculty_id": faculty_id,
            "password": creds["access_code"],
            "antibot": "HELLO",
            "captcha_token": _captcha_token("HELLO"),
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["student_id"] == faculty_id
    assert body["name"] == creds["name"]

    token = body["session_token"]
    assert ACTIVE_TOKENS[token]["role"] == "counselor"
    assert ACTIVE_TOKENS[token]["user_id"] == faculty_id


def test_faculty_id_is_case_insensitive():
    r = _client().post(
        "/api/auth/counselor-login",
        json={
            "faculty_id": "counselor02",
            "password": "counsel202",
            "antibot": "HELLO",
            "captcha_token": _captcha_token("HELLO"),
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["student_id"] == "COUNSELOR02"


def test_wrong_password_is_rejected():
    r = _client().post(
        "/api/auth/counselor-login",
        json={
            "faculty_id": "COUNSELOR03",
            "password": "definitely-wrong",
            "antibot": "HELLO",
            "captcha_token": _captcha_token("HELLO"),
        },
    )
    assert r.status_code == 401


def test_a_student_account_cannot_use_counselor_login():
    r = _client().post(
        "/api/auth/counselor-login",
        json={
            "faculty_id": "2024001",
            "password": "ACCESS123",
            "antibot": "HELLO",
            "captcha_token": _captcha_token("HELLO"),
        },
    )
    assert r.status_code == 401
