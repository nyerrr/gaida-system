"""Tests for the server-side login CAPTCHA (app/services/captcha.py)."""
import base64
import hashlib
import hmac
import time

import pytest
from fastapi import HTTPException

from app.services import captcha


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """The login endpoints share an in-memory rate limiter (5 tries/min per
    student number). These tests log in several times, so reset it before and
    after each test so they neither trip it nor leave it used up for others."""
    from app.services import rate_limiter
    rate_limiter.users_requests.clear()
    yield
    rate_limiter.users_requests.clear()


def _answer_for(token: str) -> str:
    """Brute-force the answer from a token (test only: we know the secret)."""
    nonce, exp, sig = token.split(".")
    import itertools
    for combo in itertools.product(captcha._CHARS, repeat=captcha.CAPTCHA_LENGTH):
        guess = "".join(combo)
        if hmac.compare_digest(captcha._sign(nonce, int(exp), guess), sig):
            return guess
    raise AssertionError("no answer found")


def _make(answer: str, ttl: int = 60):
    nonce = "n" + str(time.time_ns())
    exp = int(time.time()) + ttl
    return f"{nonce}.{exp}.{captcha._sign(nonce, exp, answer)}"


def test_challenge_shape_and_png():
    c = captcha.new_challenge()
    assert c["token"].count(".") == 2
    assert c["image"].startswith("data:image/png;base64,")
    png = base64.b64decode(c["image"].split(",", 1)[1])
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_token_does_not_contain_answer():
    c = captcha.new_challenge()
    assert len(c["token"].split(".")[2]) == 64  # a hex HMAC, not the code


def test_correct_answer_any_case_passes():
    token = _make("AB3KXY")
    captcha.verify_captcha(token, " ab3kxy ")  # no exception


def test_wrong_answer_rejected_and_burns_token():
    token = _make("AB3KXY")
    with pytest.raises(HTTPException) as e:
        captcha.verify_captcha(token, "WRONG1")
    assert e.value.status_code == 400
    with pytest.raises(HTTPException):  # same token, now correct answer: still dead
        captcha.verify_captcha(token, "AB3KXY")


def test_token_is_single_use():
    token = _make("QWE234")
    captcha.verify_captcha(token, "QWE234")
    with pytest.raises(HTTPException):
        captcha.verify_captcha(token, "QWE234")


def test_expired_token_rejected():
    nonce = "old" + str(time.time_ns())
    exp = int(time.time()) - 5
    token = f"{nonce}.{exp}.{captcha._sign(nonce, exp, 'ABCDEF')}"
    with pytest.raises(HTTPException):
        captcha.verify_captcha(token, "ABCDEF")


@pytest.mark.parametrize("token", ["", "garbage", "a.b", "a.b.c.d", "n.notint.sig"])
def test_malformed_token_rejected(token):
    with pytest.raises(HTTPException):
        captcha.verify_captcha(token, "ABCDEF")


def test_empty_answer_rejected():
    with pytest.raises(HTTPException):
        captcha.verify_captcha(_make("ABCDEF"), "  ")


def test_tampered_signature_rejected():
    token = _make("ABCDEF")
    nonce, exp, sig = token.split(".")
    forged = f"{nonce}.{exp}.{'0' * len(sig)}"
    with pytest.raises(HTTPException):
        captcha.verify_captcha(forged, "ABCDEF")


def test_extended_expiry_rejected():
    token = _make("ABCDEF", ttl=-5)
    nonce, exp, sig = token.split(".")
    forged = f"{nonce}.{int(time.time()) + 999}.{sig}"  # signature covers expiry
    with pytest.raises(HTTPException):
        captcha.verify_captcha(forged, "ABCDEF")


# --- Endpoint-level checks (need the full app, so imported lazily) ------------

def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def _student_body(**extra):
    body = {"student_number": "2024001", "email": "student1@ue.edu.ph",
            "access_code": "ACCESS123", "antibot": "HELLO"}
    body.update(extra)
    return body


def test_login_without_captcha_token_is_rejected():
    r = _client().post("/api/auth/login", json=_student_body())
    assert r.status_code == 400  # the old client-only check let this through


def test_login_with_valid_captcha_passes_then_replay_fails():
    c = _client()
    token = _make("HELLO")
    assert c.post("/api/auth/login", json=_student_body(captcha_token=token)).status_code == 200
    assert c.post("/api/auth/login", json=_student_body(captcha_token=token)).status_code == 400


def test_counselor_login_requires_captcha():
    c = _client()
    body = {"faculty_id": "counselor01", "password": "counsel123"}
    assert c.post("/api/auth/counselor-login", json=body).status_code == 400


def test_captcha_endpoint_returns_image_and_no_answer():
    r = _client().get("/api/auth/captcha")
    assert r.status_code == 200
    data = r.json()
    assert data["image"].startswith("data:image/png;base64,")
    assert set(data) == {"token", "image"}
    assert r.headers.get("cache-control") == "no-store"
