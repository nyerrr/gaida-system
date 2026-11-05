"""Login tokens survive a server restart when AUTH_SECRET is set."""

import os
import sys
import time
from datetime import datetime
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app.utils import auth


@pytest.fixture(autouse=True)
def _clean():
    auth.ACTIVE_TOKENS.clear()
    auth.REVOKED_TOKENS.clear()
    yield
    auth.ACTIVE_TOKENS.clear()
    auth.REVOKED_TOKENS.clear()


def _restart():
    """Simulate the server restarting: all in-memory state is gone."""
    auth.ACTIVE_TOKENS.clear()
    auth.REVOKED_TOKENS.clear()


def test_signed_token_survives_a_restart(monkeypatch):
    monkeypatch.setenv("AUTH_SECRET", "test-secret")
    token = auth.create_session_token("2024001", role="student")
    _restart()
    user = auth.validate_token(token)
    assert user["user_id"] == "2024001"
    assert user["role"] == "student"


def test_counselor_role_survives_a_restart(monkeypatch):
    monkeypatch.setenv("AUTH_SECRET", "test-secret")
    token = auth.create_session_token("COUNSELOR01", role="counselor")
    _restart()
    assert auth.validate_token(token)["role"] == "counselor"


def test_without_a_secret_tokens_are_memory_only(monkeypatch):
    monkeypatch.delenv("AUTH_SECRET", raising=False)
    token = auth.create_session_token("2024001")
    assert auth.validate_token(token) is not None
    _restart()
    assert auth.validate_token(token) is None


def test_tampered_role_is_rejected(monkeypatch):
    monkeypatch.setenv("AUTH_SECRET", "test-secret")
    token = auth.create_session_token("2024001", role="student")
    _restart()
    forged = token.replace("token_student_", "token_counselor_", 1)
    assert auth.validate_token(forged) is None


def test_token_signed_with_another_secret_is_rejected(monkeypatch):
    monkeypatch.setenv("AUTH_SECRET", "secret-one")
    token = auth.create_session_token("2024001")
    _restart()
    monkeypatch.setenv("AUTH_SECRET", "secret-two")
    assert auth.validate_token(token) is None


def test_expired_token_is_rejected(monkeypatch):
    monkeypatch.setenv("AUTH_SECRET", "test-secret")
    token = auth.create_session_token("2024001")
    _restart()
    monkeypatch.setattr(auth, "time", lambda: time.time() + 13 * 3600)
    assert auth.validate_token(token) is None


def test_logged_out_token_stays_dead(monkeypatch):
    monkeypatch.setenv("AUTH_SECRET", "test-secret")
    token = auth.create_session_token("2024001")
    auth.revoke_session_token(token)
    assert auth.validate_token(token) is None


def test_revoked_token_is_rejected_by_another_instance(monkeypatch):
    class SharedRevocations:
        def __init__(self):
            self.records = {}

        def table(self, _name):
            return Query(self.records)

    class Query:
        def __init__(self, records):
            self.records = records
            self.operation = "select"
            self.filters = []
            self.payload = None

        def upsert(self, payload, on_conflict=None):
            self.operation = "upsert"
            self.payload = payload
            return self

        def delete(self):
            self.operation = "delete"
            return self

        def select(self, *_args):
            self.operation = "select"
            return self

        def eq(self, field, value):
            self.filters.append((field, "eq", value))
            return self

        def gt(self, field, value):
            self.filters.append((field, "gt", value))
            return self

        def lt(self, field, value):
            self.filters.append((field, "lt", value))
            return self

        def limit(self, _count):
            return self

        def execute(self):
            if self.operation == "upsert":
                self.records[self.payload["token_hash"]] = self.payload
                return SimpleNamespace(data=[self.payload])
            if self.operation == "delete":
                for key, record in list(self.records.items()):
                    if any(
                        field == "expires_at"
                        and operator == "lt"
                        and datetime.fromisoformat(record[field]) < datetime.fromisoformat(value)
                        for field, operator, value in self.filters
                    ):
                        del self.records[key]
                return SimpleNamespace(data=[])

            matches = []
            for key, record in self.records.items():
                if all(
                    (record.get(field) == value if operator == "eq" else record.get(field) > value)
                    for field, operator, value in self.filters
                ):
                    matches.append(record)
            return SimpleNamespace(data=matches[:1])

    monkeypatch.setenv("AUTH_SECRET", "test-secret")
    monkeypatch.setattr(auth, "_REVOCATION_BACKEND", "supabase")
    monkeypatch.setattr(auth, "supabase", SharedRevocations())
    token = auth.create_session_token("2024001", role="student")

    # Instance A revokes it in shared storage.
    auth.revoke_session_token(token)

    # Simulate an independent instance with no process-local token or revocation state.
    auth.ACTIVE_TOKENS.clear()
    auth.REVOKED_TOKENS.clear()
    assert auth.validate_token(token) is None


def test_garbage_tokens_are_rejected(monkeypatch):
    monkeypatch.setenv("AUTH_SECRET", "test-secret")
    for bad in ("", "token_student_x", "token_student_abc.def", "a.b.c", "token_x_.."):
        assert auth.validate_token(bad) is None
