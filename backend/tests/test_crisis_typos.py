"""Misspelled crisis phrases, strangling/choking, and give-up with loss context.

Found by running the 100 pilot messages and a typo probe against the detector:

  * "i wamt to dei" / "i want to dei" came back neutral with no alert, because
    the fuzzy matcher refuses words under 5 letters (it has to, or "said"
    matches "sad").
  * "Strangling myself to stop is what it feels like" was read as anxiety.
  * "...Loss of fam members. Family problems... I just really want to give up"
    was read as stress because the message also mentions studies.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app.services.crisis_guards import resolve_crisis_level
from app.services.fuzzy_match import typo_phrase_match, typo_variants


# ── The matcher on its own ───────────────────────────────────────────────────

@pytest.mark.parametrize(
    "keyword,text",
    [
        ("i want to die", "i wamt to dei"),
        ("i want to die", "i want to dei"),
        ("i want to die", "i wnat to die"),
        ("kill myself", "kill myslef"),
        ("end my life", "end my lief"),
        ("strangling myself", "strangling myslef"),
        ("hang myself", "hnag myself"),
    ],
)
def test_single_slip_typos_match_crisis_phrases(keyword, text):
    assert typo_phrase_match(keyword, text)


@pytest.mark.parametrize(
    "keyword,text",
    [
        ("i want to die", "i want to dye my hair"),            # real word
        ("i want to die", "i dont want to dei"),                # negated
        ("i want to die", "i dont wnat to die"),                # negated
        ("i want to die", "i wanted to die yesterday"),         # not a slip
        ("kill myself", "jill myself"),                         # real name
        ("kill myself", "i will kill myself"),                  # exact: not this matcher's job
        ("want to die", "i want to be a dad"),
        ("end my life", "not end my lief"),
    ],
)
def test_typo_matcher_does_not_overreach(keyword, text):
    assert not typo_phrase_match(keyword, text)


def test_variants_never_include_the_word_itself_or_real_words():
    assert "die" not in typo_variants("die")
    assert "dei" in typo_variants("die")
    assert "dye" not in typo_variants("die")


# ── Through the whole detector ───────────────────────────────────────────────

@pytest.mark.parametrize(
    "text", ["i wamt to dei", "i want to dei", "i wnat to die"]
)
def test_misspelled_death_wish_reaches_crisis(text):
    from app.services.virtual_agent import detect_intent_and_level

    result = detect_intent_and_level(text)
    assert result["intent"] == "suicidal"
    assert result["severity"] == "Crisis"


def test_dye_my_hair_is_not_a_crisis():
    from app.services.virtual_agent import detect_intent_and_level

    result = detect_intent_and_level("i want to dye my hair")
    assert result["severity"] not in ("High", "Crisis")


@pytest.mark.parametrize(
    "text",
    [
        "Strangling myself to stop is what it feels like but i cant do anything",
        "i keep thinking about choking myself",
    ],
)
def test_strangling_or_choking_oneself_alerts(text):
    from app.services.virtual_agent import detect_intent_and_level

    result = detect_intent_and_level(text)
    assert result["intent"] == "suicidal"
    assert result["severity"] in ("High", "Crisis")


# ── Give-up with a loss, even when school is mentioned ───────────────────────

PILOT_R04_7 = (
    "I just try to focus on my studies because that's the only thing I can do "
    "right now. But with everything that has happened, Loss of fam members. "
    "Family problems. The exhaustion of the commute. I just really want to give up"
)


def test_give_up_after_a_loss_is_not_downgraded_to_stress():
    verdict = resolve_crisis_level(["i just want to give up"], PILOT_R04_7.lower())
    assert verdict["intent"] == "suicidal"
    assert verdict["confidence"] >= 0.88
    assert verdict.get("clarify") is True


def test_plain_school_give_up_is_still_just_stress():
    verdict = resolve_crisis_level(["i give up"], "i give up on this assignment")
    assert verdict["intent"] == "stress"
