"""Plain low-mood phrases must be read as sadness, not neutral.

From the Section A audit (4 counselors, 100 real messages): GAIDA read
"lately I've been feeling so down", "I need to cry" and "I'm doing fine just a
little down" as neutral, so only 31% of the counselors' sadness messages were
recognised.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app.services.crisis_guards import is_non_distress
from app.services.rule_intent import analyze_with_rules


@pytest.mark.parametrize(
    "text",
    [
        "lately I've been feeling so down, idk why",
        "I need to cry",
        "I'm doing fine just a little down",
        "I usually cry about it just to let the emotions out",
        "I think its just losing interest in studying in general",
    ],
)
def test_plain_low_mood_is_sadness(text):
    assert analyze_with_rules(text)["intent"] == "sadness"
    assert not is_non_distress(text)


@pytest.mark.parametrize(
    "text",
    [
        "please sit down",
        "this song is down to earth",
        "she is so downright rude",
        "I'm doing fine",
    ],
)
def test_ordinary_uses_of_down_are_not_sadness(text):
    assert analyze_with_rules(text)["intent"] != "sadness"
