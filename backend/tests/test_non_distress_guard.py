"""Regression tests for the Section A non-distress guard (crisis_guards.py).

Four licensed counselors audited the five-class scheme against 100 real pilot
messages (Section A, Oct 2026). The same complaint kept recurring: a message
that reports coping, relief, an ordinary activity, or a bare academic outcome
was being handed a distress label anyway. Before this guard, each of the
messages below carried a distress intent — and several paged a counselor for a
student who was describing how they were managing.

Locked in here so the guard cannot silently disappear, and so it cannot silently
over-fire on a message that does name distress.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app.services.crisis_guards import (
    is_academic_setback_without_distress,
    is_non_distress,
)
from app.services.virtual_agent import detect_intent_and_level


# The counselors' Neutral items, plus the one remaining gold-key miss.
NON_DISTRESS = [
    (
        "counsellor R02-9",
        "I enjoy it now because on my last course I feel the rush I feel burn "
        "out my last course is Architecture",
    ),
    (
        "counsellor R03-3",
        "I am enjoying my current course and not thinking to much about it but "
        "of course I still feel the rush",
    ),
    (
        "counsellor R03-7",
        "hindi ko pa naman nakikita grades ko sa ibang subject pero sa iba "
        "nakita ko na, and nakaluwag luwag naman na",
    ),
    (
        "counsellor R04-1",
        "i mean been trying to relax myself through video games and friends",
    ),
    (
        "counsellor R04-6",
        "The more urgent ones becomes my priority then move down the list and "
        "finish what i only can without being too burned out.",
    ),
    ("gold 74 (previous miss)", "I'm doing my homework right now"),
    ("coping", "I'm trying to stay focused"),
    ("relief", "I feel relieved now that exams are over"),
    ("positive", "I finally finished my project"),
]


@pytest.mark.parametrize("label,message", NON_DISTRESS)
def test_non_distress_stays_neutral_and_never_alerts(label, message):
    result = detect_intent_and_level(message)
    assert result["intent"] == "neutral", (label, result["intent"])
    assert result["anxiety_level"] is None


# A distress word anywhere vetoes the guard, even inside an otherwise routine
# or positive-sounding sentence.
DISTRESS_WITH_INNOCENT_WORDS = [
    "I'm doing my homework but I'm so anxious I can't focus",
    "I'm trying to stay focused but I feel so empty",
    "I finally finished my project and now I feel worthless",
]


@pytest.mark.parametrize("message", DISTRESS_WITH_INNOCENT_WORDS)
def test_distress_word_vetoes_the_guard(message):
    assert is_non_distress(message) is False
    assert detect_intent_and_level(message)["intent"] != "neutral"


# A negated "positive" is not evidence of calm and must not be read as coping.
NEGATED_POSITIVE = [
    "I'm not doing fine",
    "I'm not okay",
    "I don't enjoy anything anymore",
    "I can't stay focused",
]


@pytest.mark.parametrize("message", NEGATED_POSITIVE)
def test_negated_positive_is_not_read_as_coping(message):
    assert is_non_distress(message) is False


# A bare academic outcome is a fact about a stressor, not a disclosure of an
# emotion. Routed to the internal `stress` intent, never left as anxiety.
ACADEMIC_SETBACKS = [
    "I failed math",
    "I'm going to fail this subject",
    "I got a low grade in my prelim exam",
]


@pytest.mark.parametrize("message", ACADEMIC_SETBACKS)
def test_academic_setback_is_stress_not_anxiety(message):
    assert is_academic_setback_without_distress(message) is True
    result = detect_intent_and_level(message)
    assert result["intent"] == "stress"
    assert result["anxiety_level"] in (None, "low")


def test_academic_setback_with_distress_is_left_alone():
    # Gold anxiety (has an explicit distress signal) — the guard must not fire.
    message = "I'm terrified I'll fail everything and I can't turn my mind off"
    assert is_academic_setback_without_distress(message) is False
    assert detect_intent_and_level(message)["intent"] == "anxiety"


def test_crisis_beats_the_non_distress_guard():
    message = "I finished my homework and now I want to die"
    result = detect_intent_and_level(message)
    assert result["intent"] == "suicidal"
    assert result["anxiety_level"] == "crisis"


def test_loss_beats_the_non_distress_guard():
    # Carries a coping marker ("trying to stay focused") *and* a loss cue; the
    # loss path runs first, so grief keeps its own flow rather than Neutral.
    message = "we broke up days ago but I'm trying to stay focused"
    assert detect_intent_and_level(message)["intent"] == "loss"
