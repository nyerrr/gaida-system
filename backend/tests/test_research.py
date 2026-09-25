from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.api import research


class FakeInsertQuery:
    def __init__(self, table_name, stored_rows):
        self.table_name = table_name
        self.stored_rows = stored_rows

    def insert(self, row):
        self.stored_rows.append(row)
        return self

    def execute(self):
        return SimpleNamespace(data=[self.stored_rows[-1]])


class FakeSupabase:
    def __init__(self):
        self.stored_rows = []

    def table(self, table_name):
        return FakeInsertQuery(table_name, self.stored_rows)


def test_sus_submission_stores_trimmed_comment(monkeypatch):
    fake_supabase = FakeSupabase()
    monkeypatch.setattr(research, "supabase", fake_supabase)
    monkeypatch.setattr(
        research,
        "get_session",
        lambda session_id: {"user_id": "participant-1"},
    )

    payload = research.SusRequest(
        session_id="session-1",
        answers=[3] * 10,
        comment="  The chat felt easy to use.  ",
    )
    response = research.submit_sus(payload, {"user_id": "participant-1"})

    assert response.sus_score == 50.0
    assert fake_supabase.stored_rows == [
        {
            "session_id": "session-1",
            "q1": 3, "q2": 3, "q3": 3, "q4": 3, "q5": 3,
            "q6": 3, "q7": 3, "q8": 3, "q9": 3, "q10": 3,
            "sus_score": 50.0,
            "comment": "The chat felt easy to use.",
        }
    ]


def test_sus_comment_cannot_exceed_1000_characters():
    with pytest.raises(ValidationError):
        research.SusRequest(
            session_id="session-1",
            answers=[3] * 10,
            comment="x" * 1001,
        )
