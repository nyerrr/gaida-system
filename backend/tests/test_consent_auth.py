"""The consent endpoint must require an authenticated session owner.

Consent was previously writable by anyone who knew a session_id, which let an
unauthenticated caller forge consent (or later revoke it) for another user's
session. These tests pin the replacement contract: a valid bearer token is
always required, and an existing session may only be changed by its owner.
"""

import os
import sys
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from app.api import auth as auth_api
from app.main import app
from app.utils.auth import create_session_token


class FakeConsentTable:
    def __init__(self, rows):
        self.rows = rows
        self.filters = {}
        self.mode = None
        self.pending = None

    def select(self, *_args):
        self.mode = "select"
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def insert(self, row):
        self.mode = "insert"
        self.pending = dict(row)
        return self

    def update(self, values):
        self.mode = "update"
        self.pending = dict(values)
        return self

    def execute(self):
        matching = [
            row for row in self.rows
            if all(row.get(key) == value for key, value in self.filters.items())
        ]
        if self.mode == "insert":
            self.rows.append(self.pending)
            return SimpleNamespace(data=[self.pending])
        if self.mode == "update":
            for row in matching:
                row.update(self.pending)
            return SimpleNamespace(data=matching)
        return SimpleNamespace(data=matching)


class FakeSupabase:
    def __init__(self):
        self.rows = []

    def table(self, _name):
        return FakeConsentTable(self.rows)


@pytest.fixture()
def client():
    return TestClient(app)


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _consent(client, token: str | None = None, session_id: str = "session-1"):
    headers = _headers(token) if token else {}
    return client.post(
        "/api/auth/consent",
        json={"session_id": session_id, "consent_given": True},
        headers=headers,
    )


def test_consent_requires_authentication(client):
    r = _consent(client)

    assert r.status_code == 401


def test_consent_rejects_invalid_token(client):
    r = _consent(client, token="token_student_not-a-real-token")

    assert r.status_code == 401


def test_consent_rejects_another_users_existing_session(client, monkeypatch):
    token = create_session_token("2024002", role="student")
    monkeypatch.setattr(
        auth_api,
        "get_session",
        lambda _session_id: {"user_id": "2024001"},
    )

    r = _consent(client, token=token)

    assert r.status_code == 403


def test_authenticated_student_can_consent_before_session_exists(client, monkeypatch):
    token = create_session_token("2024001", role="student")
    fake_supabase = FakeSupabase()
    monkeypatch.setattr(auth_api, "get_session", lambda _session_id: None)
    monkeypatch.setattr(auth_api, "supabase", fake_supabase)

    r = _consent(client, token=token)

    assert r.status_code == 200, r.text
    assert fake_supabase.rows == [
        {"session_id": "session-1", "consent_given": True}
    ]


def test_session_owner_can_consent(client, monkeypatch):
    token = create_session_token("2024001", role="student")
    fake_supabase = FakeSupabase()
    monkeypatch.setattr(
        auth_api,
        "get_session",
        lambda _session_id: {"user_id": "2024001"},
    )
    monkeypatch.setattr(auth_api, "supabase", fake_supabase)

    r = _consent(client, token=token)

    assert r.status_code == 200, r.text
    assert fake_supabase.rows == [
        {"session_id": "session-1", "consent_given": True}
    ]


def test_research_participant_can_consent_for_own_session(client, monkeypatch):
    token = create_session_token("participant-1", role="research")
    fake_supabase = FakeSupabase()
    monkeypatch.setattr(
        auth_api,
        "get_session",
        lambda _session_id: {"user_id": "participant-1"},
    )
    monkeypatch.setattr(auth_api, "supabase", fake_supabase)

    r = _consent(client, token=token)

    assert r.status_code == 200, r.text
