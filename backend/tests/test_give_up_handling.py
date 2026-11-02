"""Soft "give up" phrases: ask, don't assume.

After the counselor interviews (Oct 2026) a vague "I give up" is treated as a
warning sign that earns a HIGH alert and one clarifying question, not a full
Crisis script. An explicit statement about death or self-harm still takes the
Crisis path, and a denial ("I don't want to give up") is not a risk at all.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app.services.crisis_guards import negated_soft_give_up, resolve_crisis_level


@pytest.mark.parametrize(
    "keyword,text",
    [
        ("i just want to give up", "i just want to give up"),
        ("i give up", "i give up"),
        ("i can't do this anymore", "i can't do this anymore"),
    ],
)
def test_vague_give_up_is_high_with_a_clarifying_question(keyword, text):
    verdict = resolve_crisis_level([keyword], text)
    assert verdict["intent"] == "suicidal"
    assert verdict["confidence"] == 0.88  # HIGH, not the 0.99 Crisis line
    assert verdict["clarify"] is True


@pytest.mark.parametrize(
    "keywords,text",
    [
        (["i want to give up this life"], "i want to give up this life"),
        (["i want to die"], "i want to die"),
        # The pipeline passes every phrase it matched; the explicit one wins.
        (["i give up", "i want to die"], "i give up, i want to die"),
    ],
)
def test_explicit_death_talk_is_still_a_full_crisis(keywords, text):
    verdict = resolve_crisis_level(keywords, text)
    assert verdict["confidence"] >= 0.99
    assert not verdict.get("clarify")


@pytest.mark.parametrize(
    "text",
    ["i don't want to give up", "don't give up on me", "hindi ako susuko"],
)
def test_denying_giving_up_is_not_a_risk(text):
    assert negated_soft_give_up(text)
    verdict = resolve_crisis_level(["give up"], text)
    assert verdict["intent"] == "neutral"


def test_giving_up_on_schoolwork_is_stress_not_a_crisis():
    verdict = resolve_crisis_level(["i give up"], "i give up on this assignment")
    assert verdict["intent"] == "stress"
    assert verdict["confidence"] < 0.75


def test_vague_give_up_through_full_pipeline():
    """The end-to-end detector (not just resolve_crisis_level) must return
    HIGH + clarify for a bare "give up", and must not reach Crisis."""
    from app.services.virtual_agent import detect_intent_and_level

    result = detect_intent_and_level("i just want to give up")
    assert result["intent"] == "suicidal"
    assert result["severity"] == "High"
    assert result["anxiety_level"] == "high"
    assert result["clarify"] is True


@pytest.mark.parametrize(
    "text",
    [
        "should i give up my scholarship",
        "i want to give up smoking",
        "i'm trying to give up coffee",
        "i want to give up vaping",
    ],
)
def test_giving_up_an_everyday_thing_is_not_a_risk(text):
    verdict = resolve_crisis_level(["i want to give up"], text)
    assert verdict["confidence"] < 0.75
    assert not verdict.get("clarify")


@pytest.mark.parametrize(
    "text",
    [
        "i want to give up drinking and i feel hopeless",
        "i give up on everything",
        "i just want to give up",
    ],
)
def test_giving_up_without_a_named_everyday_thing_still_alerts(text):
    verdict = resolve_crisis_level(["i want to give up"], text)
    assert verdict["confidence"] >= 0.88
    assert verdict.get("clarify") is True


def test_death_talk_next_to_a_habit_is_still_a_crisis():
    verdict = resolve_crisis_level(
        ["i want to die"], "i want to give up smoking and i want to die"
    )
    assert verdict["confidence"] >= 0.99
