"""Regression tests for the detection false positives catalogued against the
120-message gold key.

Every message in ORDINARY_LANGUAGE reached a false crisis, a false suicidal
label or a false counselor alert before the anchored fuzzy matcher
(app/services/fuzzy_match.py) and the negation guard (crisis_guards.py) were
added. The failure mode was always the same: an unanchored SequenceMatcher
compared a whole sentence (or a 2-token window) to a crisis keyword by overall
character similarity, so

    "I said hello to her"   matched ``sad``  -> sadness High 0.98
    "I made a cake"         matched ``mad``  -> anger
    "of myself"             matched ``off myself``  -> crisis 0.99
    "i don't want to die"   matched ``i want to die`` -> crisis 0.99

These cases are locked in so the matcher cannot silently regress to loose
substring/whole-text similarity.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.virtual_agent import detect_intent_and_level

# Ordinary, non-distressed (or mildly neutral) messages that must never be read
# as suicidal and must never reach an alerting severity.
ORDINARY_LANGUAGE = [
    "I made a cake this morning",
    "I said hello to her",
    "we talked about a wide range of topics",
    "I went to the sand and took photos",
    "I'm proud of myself",
    "I think of myself",
    "I'm tired of myself",
    "I am ashamed of myself",
    "I feel so fucking disappointed of myself bro",
    "I want to disappear for a while on vacation",
    "this class is killing me lol",
    "I'm dying of laughter",
    "im about to die laughing",
    "goodbye, see you next week",
    "I want to sleep",
    # "give up" + a non-life object is not a death wish. The assignment one is
    # also in SAFE_PHRASES; the others must not page on the life-object rule.
    "i give up on this assignment",
    "i gave up on my dreams",
    # NOTE: a bare "i just want to give up" is intentionally NOT listed here.
    # Since the October 2026 counselor interviews it is a HIGH warning sign with
    # clarify=True (not Crisis). That contract is pinned in
    # test_give_up_handling.py::test_vague_give_up_through_full_pipeline.
]

# Explicit first-person DENIALS of a death/harm wish. Negating a death verb is
# the opposite of wanting to die; only a negated LIFE verb ("i don't want to
# live") is a death wish, which is why the guard is per-keyword.
NEGATED_DENIALS = [
    "I don't want to die",
    "i do not want to die",
    "I'm not going to kill myself",
    "I don't want to hurt myself",
    "im not suicidal",
    # Negating a "give up ... life" wish is the opposite of wanting to die, so
    # the phrase must be recognised as harm by the negation guard too.
    "i don't want to give up this life",
    "i do not want to give up on life",
]

# The other half of the contract: fixing the false positives above must never
# silence a real crisis. These must still page.
GENUINE_CRISIS = [
    "im about to die",
    "i fell like dying",
    "I want to kill myself",
    "i just want to die",
    "gusto ko na mamatay",
    "mamamatay na lang ako",
    "wala na akong rason para mabuhay",
    "wala nang pag-asa, mamamatay na lang ako",
    "I want to disappear forever",
    # Surrender phrased with the speaker's own life as the object.
    "i want to give up this life",
    "i am ready to give up on life",
    # A negated give-up idiom in one clause must not cancel the plan in the
    # next ("ayoko na" is Tagalog for "I give up", not "I don't want to").
    "ayoko na, lulunukin ko lahat ng gamot",
]


def _detect(message):
    return detect_intent_and_level(message)


def test_ordinary_language_is_never_a_crisis():
    for message in ORDINARY_LANGUAGE:
        result = _detect(message)
        assert result["intent"] != "suicidal", (message, result)
        assert result["anxiety_level"] not in ("crisis", "high"), (message, result)


def test_negated_death_wishes_are_not_escalated():
    for message in NEGATED_DENIALS:
        result = _detect(message)
        assert result["intent"] != "suicidal", (message, result)
        assert result["anxiety_level"] != "crisis", (message, result)


def test_genuine_crises_still_reach_the_crisis_flow():
    for message in GENUINE_CRISIS:
        result = _detect(message)
        assert result["intent"] == "suicidal", (message, result)
        assert result["anxiety_level"] == "crisis", (message, result)


def test_immediate_external_threats_reach_the_crisis_flow():
    message = "THERES SOMETHING GOING ON RIGHT NOW, SOMEONES GONA KILL ME HELP I FELL LIKE DYING"
    for threat in ("someone is going to kill me", "someone's gonna kill me", message):
        result = _detect(threat)
        assert result["intent"] == "physical_danger", (threat, result)
        assert result["severity"] == "Crisis", (threat, result)


def test_immediate_external_threat_gets_emergency_response():
    from app.services.intent_router import stream_analyze_intent

    events = list(stream_analyze_intent(
        "THERES SOMETHING GOING ON RIGHT NOW, SOMEONES GONA KILL ME HELP I FELL LIKE DYING"
    ))
    result = events[-1]["result"]
    assert result["severity"] == "Crisis"
    assert "911 now" in result["response"].lower()
    assert "safer public place" in result["response"].lower()


def test_urgent_safety_message_bypasses_chat_rate_limit():
    from uuid import uuid4

    import pytest
    from fastapi import HTTPException

    from app.main import _check_chat_rate_limit
    from app.services.rate_limiter import users_requests

    user_id = f"safety-rate-limit-test-{uuid4()}"
    try:
        for _ in range(5):
            _check_chat_rate_limit("hello", user_id)
        with pytest.raises(HTTPException):
            _check_chat_rate_limit("hello", user_id)

        _check_chat_rate_limit("I'm about to die", user_id)

        with pytest.raises(HTTPException):
            _check_chat_rate_limit("hello", user_id)
    finally:
        users_requests.pop(user_id, None)
