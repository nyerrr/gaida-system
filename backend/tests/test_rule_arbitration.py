"""Tests for the ML-neutral fallthrough and rule/ML arbitration.

These lock in the measured behavior from score_detection.py: the gold key went
from 85.0% to 97.5% overall once a `neutral` ML vote stopped short-circuiting
the keyword rules. Every assertion here is traceable to a specific message in
backend/training/expert_validation/gold_key.csv.
"""
import csv
import os

import pytest

from app.services.crisis_guards import is_other_persons_anger
from app.services.ml_classifier import classify_intent
from app.services.rule_intent import analyze_with_rules
from app.services.virtual_agent import detect_intent_and_level

GOLD_KEY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "training",
    "expert_validation",
    "gold_key.csv",
)


def _gold():
    with open(GOLD_KEY, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


# ── The four changes, and what each one actually fixed ───────────────────────
#
# Measured on the 120-message gold key: 85.0% -> 97.5%.
#
# 1. Expanded anxiety/sadness/anger keyword lists. There was no anger list at
#    all, so all 24 gold anger messages fell through. This is the biggest win.
# 2. rule/ML arbitration at RULE_UNANIMITY. The rules are unanimous on three
#    messages the classifier is confidently wrong about.
# 3. Three-way vote split -> uncertain, instead of deferring to Logistic
#    Regression. This removed a false crisis on a hunger message.
# 4. ML `neutral` -> fall through to the rules. Only one of the original 12 was
#    a literal `neutral` vote, but the branch was still wrong.
#
# Retraining the classifier fixed none of them: it produced a byte-identical
# confusion matrix (85.0% both before and after).

ML_NEUTRAL_MESSAGES = [
    "my palms are sweating and my mind is racing right now",
    "nahihilo na ako sa kakaisip",
    "paulit-ulit kong iniisip ang mga pangyayari at di ako kumalma",
    "ang init ng ulo ko, ayoko munang kausapin kahit sino",
    "nagngangalit ako ngayon, para akong sasabog",
    "I've been crying all day and I can't stop",
    "I feel panicky and I don't know why",
    "hindi ko mapigilan ang takot na nararamdaman ko",
    "I'm raging right now, stay away from me",
    "I feel like I'm about to explode in anger",
    "it hurts so much and I don't know how to move on",
    "paulit-ulit kong inaalala ang masasakit na alaala",
]

EXPECTED = [
    "anxiety", "anxiety", "anxiety", "anger", "anger", "sadness",
    "anxiety", "anxiety", "anger", "anger", "sadness", "sadness",
]


# Correction to an earlier misreading: these 12 were NOT all ML `neutral`
# votes. Attributing them to the short-circuit branch was wrong — 10 of the 12
# vote `uncertain`, which already fell through to the keyword rules. The rules
# simply had no vocabulary for them. The `0.3` they all carried came from the
# rule path's own neutral return, which is a separate line.
#
# What actually fixed them: the expanded anxiety/sadness/anger keyword lists
# (every one now scores 1.0 except the last), the rule/ML arbitration, and the
# three-way-split fix. The ML-neutral fallthrough is still correct and still
# necessary — it is what lets "nagngangalit ako ngayon, para akong sasabog"
# reach the rules at all — but it is one of four changes, not the whole fix.
ML_NEUTRAL_LITERALLY = "nagngangalit ako ngayon, para akong sasabog"


@pytest.mark.parametrize("message,expected", list(zip(ML_NEUTRAL_MESSAGES, EXPECTED)))
def test_distress_never_lands_on_the_hardcoded_neutral_constant(message, expected):
    """None of these may return the bare 0.3 that 12 of them used to share."""
    result = detect_intent_and_level(message)
    assert result["intent"] == expected, message
    assert result["confidence"] != 0.3, f"still the hardcoded constant: {message}"


def test_literal_ml_neutral_defers_to_the_rules():
    """The one message here the classifier genuinely calls `neutral`.

    This is the branch that used to `return _build_result("neutral", 0.3)`
    before the keyword rules could run.
    """
    assert classify_intent(ML_NEUTRAL_LITERALLY)["intent"] == "neutral"
    rules = analyze_with_rules(ML_NEUTRAL_LITERALLY)
    assert rules["intent"] == "anger" and rules["confidence"] == 1.0

    result = detect_intent_and_level(ML_NEUTRAL_LITERALLY)
    assert result["intent"] == "anger"
    assert result["confidence"] != 0.3


def test_ordinary_life_still_reads_as_neutral_after_fallthrough():
    """The fallthrough must not turn every message into distress."""
    for message in [
        "I'm just watching Netflix right now",
        "I passed my math exam",
        "The weather is nice today",
        "kakain na ako kasi gutom na ako",
        "I'll go to the mall this weekend",
    ]:
        assert detect_intent_and_level(message)["intent"] == "neutral", message


# ── Three-way split must defer, never escalate ──────────────────────────────

def test_three_way_vote_is_uncertain_not_a_logistic_regression_tiebreak():
    """All three models disagreeing is the absence of signal.

    This message previously produced votes {suicidal: 1, anxiety: 1,
    neutral: 1} and let Logistic Regression's stray suicidal become a 0.74
    verdict — a counselor paged because a student said they were hungry.
    """
    result = classify_intent("kakain na ako kasi gutom na ako")
    assert result["method"] == "ml_no_majority"
    assert result["intent"] == "uncertain"
    assert len(set(result["votes"].values())) == 1

    detected = detect_intent_and_level("kakain na ako kasi gutom na ako")
    assert detected["intent"] == "neutral"
    assert detected["anxiety_level"] != "crisis"


# ── Rule/ML arbitration ──────────────────────────────────────────────────────
#
# analyze_with_rules returns the winning label's share of all matched keyword
# weight, so 1.0 means every phrase found pointed the same way. On these three
# the classifier was confidently wrong and the rules were unanimous.

ARBITRATED = [
    ("I feel so sad that I can't even eat properly", "sadness", "anxiety"),
    ("I miss them so much it hurts to breathe", "sadness", "anxiety"),
    ("I feel rejected and heartbroken right now", "sadness", "anger"),
]


@pytest.mark.parametrize("message,expected,ml_said", ARBITRATED)
def test_unanimous_rules_overrule_a_wrong_ml_vote(message, expected, ml_said):
    rules = analyze_with_rules(message)
    assert rules["confidence"] == 1.0, "arbitration requires a unanimous rule read"
    assert classify_intent(message)["intent"] == ml_said, "ML was wrong here"
    assert detect_intent_and_level(message)["intent"] == expected


def test_reported_anger_is_not_the_students_anger():
    """"my mom is angry every time I come home late" scores anger 1.0 on the
    keyword engine. Handing that student an anger-management flow answers a
    question they did not ask — they are describing a household climate."""
    message = "my mom is angry every time I come home late"
    assert analyze_with_rules(message)["intent"] == "anger"
    assert is_other_persons_anger(message)
    assert detect_intent_and_level(message)["intent"] == "neutral"

    # Reaches this through the rule path too, not just the arbitration block:
    # the classifier is unsure about it, so it never gets past `uncertain`.
    assert classify_intent(message)["intent"] != "anger"


def test_self_directed_anger_survives_the_reported_anger_guard():
    """The guard needs two parts to agree, because a possessive alone lies.

    These all contain "my <person>" or a Filipino third-party anger phrase, but
    the anger belongs to the student.
    """
    for message, expected in [
        ("my brother keeps taking my stuff and it makes me so furious", "anger"),
        ("galit ako sa sarili ko kasi ginawa ko yung paulit-ulit", "anger"),
        ("I'm so angry at my roommate", "anger"),
    ]:
        assert not is_other_persons_anger(message), message
        assert detect_intent_and_level(message)["intent"] == expected, message


def test_anger_never_pages_a_counselor():
    """Anger is capped in _build_result so a rant is never an incident."""
    for message in [
        "I'm raging right now, stay away from me",
        "my phone died and I'm so mad about it",
        "I could actually scream at the top of my lungs",
    ]:
        result = detect_intent_and_level(message)
        assert result["intent"] == "anger", message
        assert result["anxiety_level"] != "crisis", message
        assert result["confidence"] <= 0.55, message


def test_arbitration_can_never_touch_a_crisis():
    """A suicidal ML vote is left alone, and rules cannot switch a crisis off."""
    for message in [
        "I want to kill myself",
        "I don't see the point of living anymore",
        "suko na ako sa buhay",
    ]:
        result = detect_intent_and_level(message)
        assert result["intent"] == "suicidal", message
        assert result["anxiety_level"] == "crisis", message


# ── Full gold key ────────────────────────────────────────────────────────────

def test_gold_key_overall_accuracy_is_at_least_95_percent():
    """Guards the 97.5% measured after the arbitration change.

    Lives here rather than only in the scorer so a regression fails the normal
    test run instead of waiting for someone to remember to re-score.
    """
    rows = _gold()
    correct = sum(
        1
        for r in rows
        if detect_intent_and_level(r["text"])["intent"] == r["gold_label"]
    )
    pct = 100.0 * correct / len(rows)
    assert pct >= 95.0, f"gold key accuracy fell to {pct:.1f}% ({correct}/{len(rows)})"


def test_gold_key_has_no_false_crises():
    """An unnecessary alert is recoverable; a missed one is not.

    Every gold-neutral message must stay out of the crisis flow, and no
    gold-sadness message may be escalated into one.
    """
    rows = _gold()
    for r in rows:
        if r["gold_label"] == "suicidal":
            continue
        result = detect_intent_and_level(r["text"])
        assert result["anxiety_level"] != "crisis", (
            f"false crisis on gold-{r['gold_label']}: {r['text']}"
        )


def test_every_gold_suicidal_message_reaches_the_crisis_flow():
    """The safety-critical invariant. Was 15/24 before the lexicon work."""
    rows = [r for r in _gold() if r["gold_label"] == "suicidal"]
    missed = [
        r["text"]
        for r in rows
        if detect_intent_and_level(r["text"])["anxiety_level"] != "crisis"
    ]
    assert not missed, f"{len(missed)} suicidal messages missed the crisis flow: {missed}"
