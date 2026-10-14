"""Regression lock for the dry-run / persistence guard.

WHY THIS EXISTS
---------------
Running detection tests through the real pipeline used to insert genuine-looking
rows into the shared Supabase database. In particular, every crisis case in
``tests/test_detection.py`` fired ``process_alert`` → ``INSERT`` into
``counselor_alerts``, so the counselor dashboard accumulated dozens of fake
"pending Crisis" alerts and counselors received alert emails — while the
students were fictional.

``GAIDA_DISABLE_PERSISTENCE=1`` (see ``app.utils.config.persistence_disabled``)
puts the process in dry-run mode: reads still work, detection is unchanged, but
sessions / interactions / alerts are not written and no one is emailed. The
pytest suite sets it globally in ``tests/conftest.py``; these tests pin the
behaviour down so a future refactor cannot silently reintroduce DB writes.
"""

import pytest

from app.utils.config import persistence_disabled


class _Recorder:
    """Minimal stand-in for the Supabase client that records writes."""

    def __init__(self):
        self.tables_read = []
        self.inserts = []

    def table(self, name):
        self.tables_read.append(name)
        return self

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def insert(self, payload):
        self.inserts.append(payload)
        return self

    def update(self, *args, **kwargs):
        self.inserts.append(("update", args, kwargs))
        return self

    def execute(self):
        return self


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_flag_truthy_values_enable_dry_run(monkeypatch, value):
    monkeypatch.setenv("GAIDA_DISABLE_PERSISTENCE", value)
    assert persistence_disabled() is True


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off"])
def test_flag_falsy_values_keep_persistence(monkeypatch, value):
    monkeypatch.setenv("GAIDA_DISABLE_PERSISTENCE", value)
    assert persistence_disabled() is False


def test_start_session_does_not_write_when_disabled(monkeypatch):
    monkeypatch.setenv("GAIDA_DISABLE_PERSISTENCE", "1")
    import app.database.database as db
    from app.services import session_manager as sm

    recorder = _Recorder()
    monkeypatch.setattr(db, "supabase", recorder)

    sid = sm.start_session(user_id=None)
    try:
        assert sid in sm.SESSIONS, "in-memory session must still exist"
        assert recorder.inserts == [], "dry-run must not INSERT a session row"
    finally:
        sm.SESSIONS.pop(sid, None)


def test_start_session_writes_when_enabled(monkeypatch):
    monkeypatch.setenv("GAIDA_DISABLE_PERSISTENCE", "0")
    import app.database.database as db
    from app.services import session_manager as sm

    recorder = _Recorder()
    monkeypatch.setattr(db, "supabase", recorder)

    sid = sm.start_session(user_id=None)
    try:
        assert "sessions" in recorder.tables_read
        assert recorder.inserts, "persistence on must INSERT a session row"
    finally:
        sm.SESSIONS.pop(sid, None)


def test_persist_session_data_is_noop_when_disabled(monkeypatch):
    monkeypatch.setenv("GAIDA_DISABLE_PERSISTENCE", "1")
    from app.services import session_manager as sm

    class _Boom:
        def table(self, *args, **kwargs):
            raise AssertionError("dry-run touched the database")

    monkeypatch.setattr(sm, "supabase", _Boom())

    # Must return before the consent check / insert — no exception raised.
    sm._persist_session_data("sess-dry-run", {"sender": "user", "text": "hi"})


def test_process_alert_skips_db_and_email_when_disabled(monkeypatch):
    monkeypatch.setenv("GAIDA_DISABLE_PERSISTENCE", "1")
    import app.database.database as db
    from app.api import counselor

    recorder = _Recorder()
    monkeypatch.setattr(db, "supabase", recorder)
    monkeypatch.setattr(counselor, "ALERTS", [])

    emailed = []
    import app.services.notifications as notifications
    monkeypatch.setattr(
        notifications,
        "send_counselor_alert_email",
        lambda **kwargs: emailed.append(kwargs),
    )

    result = counselor.process_alert(
        session_id="sess-dry-run-alert",
        user_id=None,
        intent="suicidal",
        anxiety_score=95,
        message="i want to die",
        severity="Crisis",
    )

    assert result["severity"] == "Crisis"
    assert recorder.inserts == [], "dry-run must not INSERT an alert row"
    assert emailed == [], "dry-run must not email counselors"


def test_process_alert_writes_when_enabled(monkeypatch):
    monkeypatch.setenv("GAIDA_DISABLE_PERSISTENCE", "0")
    import app.database.database as db
    from app.api import counselor

    recorder = _Recorder()
    monkeypatch.setattr(db, "supabase", recorder)
    monkeypatch.setattr(counselor, "ALERTS", [])

    import app.services.notifications as notifications
    monkeypatch.setattr(
        notifications, "send_counselor_alert_email", lambda **kwargs: None
    )

    counselor.process_alert(
        session_id="sess-write",
        user_id=None,
        intent="suicidal",
        anxiety_score=95,
        message="i want to die",
        severity="Crisis",
    )

    assert any(isinstance(i, dict) and i.get("severity") == "Crisis" for i in recorder.inserts)
