"""Signed participant tokens for anonymous research participants.

The anonymous participant credential used to be a plain code looked up in the
database. It is now a signed token, so a raw or tampered code is rejected
before any lookup. These tests pin the token format and the endpoint wiring
for start/check/withdraw, including rejection of guessable legacy codes.
"""
import os
import sys
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

pytest.importorskip("fastapi")

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api import research
from app.main import app
from app.services import rate_limiter
from app.utils import auth
from app.utils.auth import get_research_access
from app.utils.participant_token import (
    TOKEN_PREFIX,
    create_participant_token,
    verify_participant_token,
)


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    monkeypatch.setenv("PARTICIPANT_TOKEN_SECRET", "participant-test-secret")
    rate_limiter.users_requests.clear()
    auth.ACTIVE_TOKENS.clear()
    auth.REVOKED_TOKENS.clear()
    yield
    rate_limiter.users_requests.clear()
    auth.ACTIVE_TOKENS.clear()
    auth.REVOKED_TOKENS.clear()


@pytest.fixture()
def client():
    # These tests are about the participant credential, not the CAPTCHA-gated
    # research access token (covered separately in test_research_access.py).
    app.dependency_overrides[get_research_access] = lambda: {"role": "research_access"}
    yield TestClient(app)
    app.dependency_overrides.clear()


class FakeQuery:
    def __init__(self, fake, table_name):
        self.fake = fake
        self.table_name = table_name
        self.operation = None
        self.payload = None
        self.filters = {}

    def insert(self, row):
        self.operation = "insert"
        self.payload = row
        return self

    def update(self, row):
        self.operation = "update"
        self.payload = row
        return self

    def select(self, *_columns):
        self.operation = "select"
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def eq(self, column, value):
        self.filters[column] = value
        return self

    def in_(self, column, values):
        self.filters[column] = values
        return self

    def limit(self, _count):
        return self

    def execute(self):
        self.fake.calls.append(
            (self.table_name, self.operation, self.payload, dict(self.filters))
        )
        if self.table_name == "sessions" and self.operation == "select":
            return SimpleNamespace(data=self.fake.session_rows)
        if self.table_name == "research_participants" and self.operation == "select":
            return SimpleNamespace(data=self.fake.participant_rows)
        if self.operation == "delete":
            return SimpleNamespace(data=[{"deleted": True}])
        return SimpleNamespace(data=[self.payload] if self.payload else [])


class FakeSupabase:
    def __init__(self, session_rows=None, participant_rows=None):
        self.session_rows = session_rows or []
        self.participant_rows = participant_rows or []
        self.calls = []

    def table(self, table_name):
        return FakeQuery(self, table_name)


def _prepare_start(monkeypatch, existing=None, supabase=None):
    monkeypatch.setattr(research, "_fetch_participant", lambda _participant_id: existing)
    monkeypatch.setattr(research, "start_session", lambda **_kwargs: None)
    monkeypatch.setattr(
        research, "create_session_token", lambda *_args, **_kwargs: "session-token"
    )
    fake = supabase or FakeSupabase()
    monkeypatch.setattr(research, "supabase", fake)
    return fake


# ---------------------------------------------------------------------------
# Token format
# ---------------------------------------------------------------------------
def test_token_round_trip_reveals_the_bound_participant():
    token = create_participant_token("anon_0123456789")

    assert token.startswith(TOKEN_PREFIX)
    assert verify_participant_token(token) == {
        "participant_id": "anon_0123456789",
        "code": "0123456789",
    }


def test_a_modified_payload_is_rejected():
    token = create_participant_token("anon_0123456789")
    other = create_participant_token("anon_aaaaaaaaaa")
    body = token[len(TOKEN_PREFIX):].split(".", 1)[0]
    other_body = other[len(TOKEN_PREFIX):].split(".", 1)[0]

    tampered = token.replace(body, other_body)

    assert verify_participant_token(tampered) is None


def test_a_raw_code_is_not_a_token():
    assert verify_participant_token("0123456789") is None


def test_a_token_does_not_verify_under_another_secret(monkeypatch):
    token = create_participant_token("anon_0123456789")
    monkeypatch.setenv("PARTICIPANT_TOKEN_SECRET", "different-secret")

    assert verify_participant_token(token) is None


def test_a_non_anonymous_participant_id_cannot_be_signed():
    with pytest.raises(ValueError):
        create_participant_token("20240001234")


def test_a_participant_token_is_not_a_session_token():
    token = create_participant_token("anon_0123456789")

    with pytest.raises(HTTPException):
        auth.get_current_user(f"Bearer {token}")


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------
def test_resolver_accepts_a_signed_token():
    token = create_participant_token("anon_0123456789")

    participant_id, code, used_signed = research._resolve_participant_id(
        True, None, None, token
    )

    assert (participant_id, code, used_signed) == (
        "anon_0123456789",
        "0123456789",
        True,
    )


def test_resolver_rejects_a_legacy_code():
    with pytest.raises(HTTPException) as error:
        research._resolve_participant_id(True, None, "0123456789", None)

    assert error.value.status_code == 400


def test_resolver_rejects_a_tampered_token():
    token = create_participant_token("anon_0123456789")[:-1] + "x"

    with pytest.raises(HTTPException) as error:
        research._resolve_participant_id(True, None, None, token)

    assert error.value.status_code == 400


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
def test_new_anonymous_start_returns_a_token_to_save(client, monkeypatch):
    _prepare_start(monkeypatch)

    response = client.post("/api/research/start", json={"anonymous": True})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["anonymous"] is True
    assert body["participant_token_issued"] is True
    claims = verify_participant_token(body["participant_token"])
    assert claims["participant_id"] == body["participant_id"]
    assert body["participant_id"] == f"anon_{claims['code']}"


def test_returning_participant_is_not_asked_to_save_the_same_token(client, monkeypatch):
    _prepare_start(
        monkeypatch,
        existing={"year_level": "2", "program": "BS", "gender": "female", "region": "NCR"},
    )
    token = create_participant_token("anon_0123456789")

    response = client.post(
        "/api/research/start",
        json={"anonymous": True, "participant_token": token},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["participant_id"] == "anon_0123456789"
    assert body["participant_token"] == token
    assert body["participant_token_issued"] is False


def test_start_rejects_a_legacy_code_before_touching_the_database(client, monkeypatch):
    fake = _prepare_start(monkeypatch, existing={"year_level": "2"})

    response = client.post(
        "/api/research/start",
        json={"anonymous": True, "participant_code": "0123456789"},
    )

    assert response.status_code == 400
    assert fake.calls == []


def test_start_rejects_a_tampered_token_before_touching_the_database(client, monkeypatch):
    fake = _prepare_start(monkeypatch)
    token = create_participant_token("anon_0123456789")[:-1] + "x"

    response = client.post(
        "/api/research/start",
        json={"anonymous": True, "participant_token": token},
    )

    assert response.status_code == 400
    assert fake.calls == []


def test_participant_check_accepts_a_valid_token(client, monkeypatch):
    monkeypatch.setattr(
        research, "_fetch_participant", lambda _participant_id: {"year_level": "2"}
    )
    token = create_participant_token("anon_0123456789")

    response = client.post(
        "/api/research/participant-check",
        json={"anonymous": True, "participant_token": token},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"is_returning": True}


def test_participant_check_rejects_a_tampered_token(client, monkeypatch):
    monkeypatch.setattr(
        research, "_fetch_participant", lambda _participant_id: {"year_level": "2"}
    )
    token = create_participant_token("anon_0123456789")[:-1] + "x"

    response = client.post(
        "/api/research/participant-check",
        json={"anonymous": True, "participant_token": token},
    )

    assert response.status_code == 400


def test_withdraw_uses_the_participant_bound_into_the_token(client, monkeypatch):
    token = create_participant_token("anon_0123456789")
    fake = FakeSupabase(
        session_rows=[{"session_token": "session-1"}],
        participant_rows=[{"participant_id": "anon_0123456789"}],
    )
    monkeypatch.setattr(research, "supabase", fake)

    response = client.post(
        "/api/research/withdraw",
        json={"participant_token": token},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["deleted_sessions"] == 1
    assert body["participant_removed"] is True
    assert any(
        table == "sessions"
        and operation == "delete"
        and filters.get("participant_code") == "0123456789"
        for table, operation, _payload, filters in fake.calls
    )


def test_withdraw_rejects_a_tampered_token_before_touching_the_database(client, monkeypatch):
    fake = FakeSupabase()
    monkeypatch.setattr(research, "supabase", fake)
    token = create_participant_token("anon_0123456789")[:-1] + "x"

    response = client.post(
        "/api/research/withdraw",
        json={"participant_token": token},
    )

    assert response.status_code == 400
    assert fake.calls == []


def test_withdraw_requires_a_credential(client, monkeypatch):
    fake = FakeSupabase()
    monkeypatch.setattr(research, "supabase", fake)

    response = client.post("/api/research/withdraw", json={})

    assert response.status_code == 400
    assert fake.calls == []
