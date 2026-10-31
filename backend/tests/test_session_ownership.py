"""Session ownership must come from the token, not the request body.

Covers the two P0 gaps found in the audit:
  * /api/session/start trusted payload.user_id (session shadowing)
  * /api/session/message recorded data before checking ownership
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

pytest.importorskip("fastapi")  # keep collection friendly in minimal envs

from fastapi.testclient import TestClient

from app.main import app
from app.utils.auth import create_session_token


@pytest.fixture()
def client():
    return TestClient(app)


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _start(client, token: str, user_id: str | None = None) -> str:
    body = {"user_id": user_id} if user_id is not None else {}
    r = client.post("/api/session/start", json=body, headers=_headers(token))
    assert r.status_code == 200, r.text
    return r.json()["session_id"]


def test_start_session_ignores_client_supplied_user_id(client):
    token = create_session_token("2024001", role="student")
    sid = _start(client, token, user_id="2024999")

    r = client.get(f"/api/session/{sid}", headers=_headers(token))
    assert r.status_code == 200, r.text
    assert r.json()["user_id"] == "2024001"


def test_student_cannot_post_into_another_students_session(client):
    alice = create_session_token("2024001", role="student")
    bob = create_session_token("2024002", role="student")
    sid = _start(client, alice)

    r = client.post(
        "/api/session/message",
        json={"session_id": sid, "sender": "user", "text": "injected"},
        headers=_headers(bob),
    )
    assert r.status_code == 403

    state = client.get(f"/api/session/{sid}", headers=_headers(alice)).json()
    assert all(m.get("text") != "injected" for m in state["messages"])


def test_owner_can_post_into_own_session(client):
    token = create_session_token("2024001", role="student")
    sid = _start(client, token)

    r = client.post(
        "/api/session/message",
        json={"session_id": sid, "sender": "user", "text": "hello"},
        headers=_headers(token),
    )
    assert r.status_code == 200, r.text

    state = client.get(f"/api/session/{sid}", headers=_headers(token)).json()
    assert any(m.get("text") == "hello" for m in state["messages"])


def test_student_cannot_impersonate_a_counselor(client):
    token = create_session_token("2024001", role="student")
    sid = _start(client, token)

    r = client.post(
        "/api/session/message",
        json={"session_id": sid, "sender": "counselor", "text": "I am a counselor"},
        headers=_headers(token),
    )
    assert r.status_code == 403


def test_counselor_can_write_into_a_students_session(client):
    student = create_session_token("2024001", role="student")
    counselor = create_session_token("COUNSELOR01", role="counselor")
    sid = _start(client, student)

    r = client.post(
        "/api/session/message",
        json={"session_id": sid, "sender": "counselor", "text": "I'm here to help"},
        headers=_headers(counselor),
    )
    assert r.status_code == 200, r.text
