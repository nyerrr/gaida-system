"""Alert threshold, ordering and portal-redirect behaviour.

Decided with the guidance counselors (Oct 2026 interviews):
  * Moderate, High and Crisis all appear on the counselor Alerts tab.
  * The list is ordered Crisis first, then High, then Moderate.
  * Moderate is listed silently: it does not email a counselor or ring the
    dashboard. High and Crisis do.
  * A student who asks to meet a counselor in person is pointed to the UE
    Student Portal (Guidance Services -> Counseling) instead of GAIDA booking it.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app.api import counselor
from app.api.counselor import (
    ALERT_SEVERITIES,
    URGENT_SEVERITIES,
    process_alert,
    should_alert_counselor,
    sort_alerts_by_severity,
)


@pytest.fixture(autouse=True)
def _clean_alerts():
    counselor.ALERTS.clear()
    yield
    counselor.ALERTS.clear()


@pytest.mark.parametrize("severity", ["Moderate", "High", "Crisis"])
def test_moderate_and_above_alert(severity):
    assert should_alert_counselor(severity)


@pytest.mark.parametrize("severity", ["Normal", "Low", None, ""])
def test_below_moderate_does_not_alert(severity):
    assert not should_alert_counselor(severity)


def test_moderate_is_listed_but_not_urgent():
    assert "Moderate" in ALERT_SEVERITIES
    assert "Moderate" not in URGENT_SEVERITIES
    assert set(URGENT_SEVERITIES) == {"High", "Crisis"}


def test_alerts_are_ordered_crisis_then_high_then_moderate():
    alerts = [
        {"session_id": "mod-new", "severity": "Moderate", "timestamp": "2026-10-30T06:00:00Z"},
        {"session_id": "crisis-old", "severity": "Crisis", "timestamp": "2026-10-30T01:00:00Z"},
        {"session_id": "high-old", "severity": "High", "timestamp": "2026-10-30T03:00:00Z"},
        {"session_id": "mod-old", "severity": "Moderate", "timestamp": "2026-10-30T05:00:00Z"},
        {"session_id": "high-new", "severity": "High", "timestamp": "2026-10-30T07:00:00Z"},
    ]
    order = [a["session_id"] for a in sort_alerts_by_severity(alerts)]
    assert order == ["crisis-old", "high-new", "high-old", "mod-new", "mod-old"]


def test_moderate_alert_is_created_and_marked_sent():
    result = process_alert("s1", "u1", "anxiety", 3, "so stressed", "Moderate")
    assert result["alert_sent"] is True
    assert [a["severity"] for a in counselor.ALERTS] == ["Moderate"]


def test_low_does_not_create_an_alert():
    result = process_alert("s1", "u1", "anxiety", 1, "a bit tired", "Low")
    assert result["alert_sent"] is False
    assert counselor.ALERTS == []


def test_alert_upgrades_when_the_session_gets_worse_and_never_downgrades():
    process_alert("s1", "u1", "anxiety", 3, "stressed", "Moderate")
    process_alert("s1", "u1", "anxiety", 5, "much worse", "High")
    assert len(counselor.ALERTS) == 1
    assert counselor.ALERTS[0]["severity"] == "High"

    process_alert("s1", "u1", "suicidal", 5, "crisis", "Crisis")
    assert counselor.ALERTS[0]["severity"] == "Crisis"

    process_alert("s1", "u1", "anxiety", 3, "calmer now", "Moderate")
    assert counselor.ALERTS[0]["severity"] == "Crisis"


def test_a_students_own_request_sits_below_moderate_in_the_list():
    alerts = [
        {"session_id": "req", "severity": "Requested", "timestamp": "2026-10-30T09:00:00Z"},
        {"session_id": "mod", "severity": "Moderate", "timestamp": "2026-10-30T01:00:00Z"},
        {"session_id": "high", "severity": "High", "timestamp": "2026-10-30T02:00:00Z"},
    ]
    order = [a["session_id"] for a in sort_alerts_by_severity(alerts)]
    assert order == ["high", "mod", "req"]


def test_a_later_moderate_message_upgrades_a_students_request():
    counselor.ALERTS.append(
        {
            "session_id": "s1",
            "severity": "Requested",
            "status": "pending",
            "timestamp": "2026-10-30T01:00:00Z",
            "anxiety_score": 0,
        }
    )
    process_alert("s1", "u1", "anxiety", 3, "stressed", "Moderate")
    assert counselor.ALERTS[0]["severity"] == "Moderate"


# --- Counselor emails: one per escalation, never two ----------------------


@pytest.fixture
def emails(monkeypatch):
    sent = []
    monkeypatch.setattr(
        counselor,
        "_send_alert_email",
        lambda session_id, severity, intent, message: sent.append((session_id, severity)),
    )
    return sent


def test_pending_moderate_reaching_high_sends_exactly_one_email(emails):
    process_alert("s1", "u1", "anxiety", 3, "stressed", "Moderate")
    process_alert("s1", "u1", "anxiety", 5, "much worse", "High")
    process_alert("s1", "u1", "anxiety", 5, "still bad", "High")
    assert emails == [("s1", "High")]


def test_reviewed_moderate_reopened_by_high_sends_exactly_one_email(emails):
    process_alert("s1", "u1", "anxiety", 3, "stressed", "Moderate")
    counselor.ALERTS[0]["status"] = "reviewed"
    result = process_alert("s1", "u1", "anxiety", 5, "much worse", "High")
    assert emails == [("s1", "High")]
    assert counselor.ALERTS[0]["status"] == "pending"
    assert counselor.ALERTS[0]["acknowledged"] is False
    assert result["alert_sent"] is True


def test_repeated_moderate_messages_never_email(emails):
    process_alert("s1", "u1", "anxiety", 3, "stressed", "Moderate")
    process_alert("s1", "u1", "anxiety", 3, "still stressed", "Moderate")
    assert emails == []


# --- Face-to-face request -> UE Student Portal -------------------------------

from app.services.intent_router import (  # noqa: E402
    PORTAL_REDIRECT_EN,
    _portal_redirect_reply,
    wants_face_to_face_session,
)


@pytest.mark.parametrize(
    "message",
    [
        "I want to see a counselor in person",
        "can i book an appointment with the guidance counselor",
        "I'd like a face to face session with my guidance counselor",
        "How do I schedule a counseling session?",
        "gusto kong makipagkita sa counselor nang personal",
        "paano ako magpa-schedule ng counseling",
    ],
)
def test_face_to_face_requests_are_recognised(message):
    assert wants_face_to_face_session(message)


@pytest.mark.parametrize(
    "message",
    [
        "I met my counselor yesterday and it went badly",
        "I need a counselor right now",
        "I'm so stressed about my exam schedule",
        "I want to give up on this semester",
        "my friend has an appointment tomorrow",
        "I want to talk to someone",
    ],
)
def test_other_messages_are_not_treated_as_booking_requests(message):
    assert not wants_face_to_face_session(message)


def test_redirect_points_to_the_portal_for_non_urgent_students():
    turn = {"severity": "Low"}
    reply = _portal_redirect_reply(turn, "I want to see a counselor in person")
    assert reply == PORTAL_REDIRECT_EN
    assert "Student Portal" in reply and "Guidance Services" in reply


@pytest.mark.parametrize("severity", ["High", "Crisis"])
def test_redirect_never_replaces_the_reply_for_a_student_in_distress(severity):
    turn = {"severity": severity}
    assert _portal_redirect_reply(turn, "I want to see a counselor in person") is None
