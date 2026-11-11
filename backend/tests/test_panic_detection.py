"""Regression tests for panic / acute breathing distress.

These lock in the fix for a real session where the first four turns of a panic
conversation were persisted as:

    "i am panicking right now"                  -> anger  0.375  Normal
    "i have an upcoming exam"                   -> anger  0.375  Normal
    "i don't know i can;t breathe properly"     -> anxiety 0.475  Low
    "help me"                                   -> anxiety 0.475  Low

Three separate faults produced that:
  * the rule engine could not match "panicking" (only the 5-letter "panic"),
    so the classifier's wrong `anger` vote was never corrected;
  * the first turn was blended against a 0.3 placeholder history, pushing a
    real Low reading below the Normal threshold;
  * "can;t breathe" missed the urgent-physical check because the semicolon
    broke the literal match.
"""
import os

os.environ.setdefault("GAIDA_DISABLE_PERSISTENCE", "1")

import pytest

from app.services.intent_router import _detect_urgent, _prepare_turn
from app.services.rule_intent import analyze_with_rules
from app.services.session_manager import SESSIONS, start_session
from app.services.virtual_agent import (
    _build_result,
    _is_panic_disclosure,
    detect_intent_and_level,
)

PANIC_MESSAGE = "i am panicking right now"
EXAM_MESSAGE = "i have an upcoming exam"
BREATH_MESSAGE = "i don't know i can;t breathe properly"
HELP_MESSAGE = "help me"


@pytest.fixture
def live_session():
    sid = start_session()
    try:
        yield sid
    finally:
        SESSIONS.pop(sid, None)


# ── Label: panic is anxiety, never anger ─────────────────────────────────────

def test_panicking_is_classified_as_anxiety_not_anger():
    result = detect_intent_and_level(PANIC_MESSAGE)
    assert result["intent"] == "anxiety"
    assert result["severity"] != "Normal"


def test_rule_engine_recognises_panicking():
    assert analyze_with_rules(PANIC_MESSAGE)["intent"] == "anxiety"


def test_reported_panic_is_not_the_students_panic():
    # Somebody else's panic attack is not a first-person disclosure, so the
    # panic override must not relabel it as the student's anxiety.
    assert _is_panic_disclosure(PANIC_MESSAGE)
    assert not _is_panic_disclosure("my friend had a panic attack")
    assert not _is_panic_disclosure("she panicked during the exam")


# ── Typo tolerance: "can;t" must still be urgent ─────────────────────────────

@pytest.mark.parametrize(
    "message",
    [
        BREATH_MESSAGE,
        "i cant breathe",
        "i can't breathe properly",
        "i can’t get enough air",
        "hard to breathe right now",
    ],
)
def test_breathing_distress_is_urgent(message):
    assert _detect_urgent(message), message


def test_breathing_typo_reaches_at_least_moderate():
    result = detect_intent_and_level(BREATH_MESSAGE)
    assert result["intent"] == "anxiety"
    assert result["severity"] in ("Moderate", "High")


# ── First turn must not be smoothed into Normal by a fake history ────────────

def test_first_turn_panic_is_not_logged_as_normal():
    result = detect_intent_and_level(PANIC_MESSAGE)
    assert result["severity"] != "Normal"
    assert result["anxiety_score"] >= 1


def test_the_original_four_turn_sequence_stays_out_of_normal(live_session):
    first = _prepare_turn(PANIC_MESSAGE, live_session)
    assert first["intent"] == "anxiety"
    assert first["severity"] in ("Moderate", "High")
    assert first["anxiety_score"] >= 3

    _prepare_turn(EXAM_MESSAGE, live_session)
    breath = _prepare_turn(BREATH_MESSAGE, live_session)
    assert breath["intent"] == "anxiety"
    assert breath["severity"] in ("Moderate", "High")

    help_turn = _prepare_turn(HELP_MESSAGE, live_session)
    assert help_turn["intent"] == "anxiety"
    assert help_turn["severity"] != "Normal"


def test_neutral_first_turn_is_still_normal(live_session):
    # The floor must not manufacture distress out of an ordinary message.
    result = _prepare_turn("i have an upcoming exam", live_session)
    assert result["intent"] == "neutral"
    assert result["severity"] == "Normal"
    assert result["anxiety_score"] == 0


def test_vent_mode_persists_confident_acoustic_severity(live_session, monkeypatch):
    session = SESSIONS[live_session]
    session["meta"]["pending_acoustic"] = {
        "severity": "Moderate",
        "emotion": "anxious",
        "confidence": 0.9,
    }
    monkeypatch.setattr(
        "app.services.intent_router.detect_intent_and_level",
        lambda _message: _build_result("neutral", 0.3),
    )

    result = _prepare_turn(
        "you gotta gotta love me harder",
        session_id=live_session,
        vent_mode=True,
    )

    assert result["intent"] == "neutral"
    assert result["severity"] == "Moderate"
    assert result["anxiety_score"] == 3
    assert result["anxiety_level"] == "venting"
    assert session["meta"]["pending_acoustic"] is None


def test_talk_mode_uses_anxious_voice_for_reply_guidance(live_session, monkeypatch):
    session = SESSIONS[live_session]
    session["meta"]["pending_acoustic"] = {
        "severity": "Moderate",
        "emotion": "anxious",
        "confidence": 0.9,
    }
    monkeypatch.setattr(
        "app.services.intent_router.detect_intent_and_level",
        lambda _message: _build_result("neutral", 0.3),
    )

    result = _prepare_turn("a spoken lyric", session_id=live_session)

    assert result["intent"] == "neutral"
    assert result["severity"] == "Moderate"
    assert result["anxiety_level"] == "moderate"
    assert result["anxiety_score"] == 3
