"""Exact probability -> distress severity boundaries.

Required ranges (backend is the source of truth):

    Normal   0.00 - 0.44   GPT responds freely, no protocol
    Low      0.45 - 0.70   counselor protocol injected
    Moderate 0.71 - 0.76   stronger counselor protocol injected
    High     0.77 - 0.98   counselor alert + high-risk protocol
    Crisis   0.99 - 1.00   crisis protocol + immediate escalation

Every boundary value is covered here so the bands cannot drift apart or leave a
gap/overlap between adjacent severities.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app.api import counselor
from app.api.counselor import (
    URGENT_SEVERITIES,
    _sse_session_severity,
    process_alert,
    should_alert_counselor,
)
from app.services.virtual_agent import (
    COUNSELOR_PROTOCOLS,
    CRISIS_CONFIDENCE,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MODERATE,
    _build_result,
)


@pytest.fixture(autouse=True)
def _clean_alerts():
    counselor.ALERTS.clear()
    yield
    counselor.ALERTS.clear()


BOUNDARIES = [
    # confidence, severity, anxiety_level, anxiety_score
    (0.44, "Normal", None, 0),
    (0.45, "Low", "low", 1),
    (0.70, "Low", "low", 1),
    (0.71, "Moderate", "moderate", 3),
    (0.76, "Moderate", "moderate", 3),
    (0.77, "High", "high", 5),
    (0.98, "High", "high", 5),
    (0.99, "Crisis", "crisis", 5),
    (1.00, "Crisis", "crisis", 5),
]


@pytest.mark.parametrize("confidence,severity,level,score", BOUNDARIES)
def test_boundary_confidence_maps_to_exact_severity(confidence, severity, level, score):
    # "anxiety" avoids the anger cap and grief floor, which intentionally
    # override the raw confidence band.
    result = _build_result("anxiety", confidence)
    assert result["severity"] == severity
    assert result["confidence"] == confidence
    assert result["anxiety_score"] == score
    assert result["anxiety_level"] == level


def test_band_constants_match_required_ranges():
    assert SEVERITY_LOW == 0.45
    assert SEVERITY_MODERATE == 0.71
    assert SEVERITY_HIGH == 0.77
    assert CRISIS_CONFIDENCE == 0.99


@pytest.mark.parametrize(
    "confidence,expected",
    [
        (0.44, "Normal"),
        (0.45, "Low"),
        (0.70, "Low"),
        (0.71, "Moderate"),
        (0.76, "Moderate"),
        (0.77, "High"),
        (0.98, "High"),
        (0.99, "Crisis"),
        (1.00, "Crisis"),
    ],
)
def test_dashboard_mirror_uses_the_same_bands(confidence, expected):
    """The SSE/active-session fallback must label a session exactly like the
    band that fired in the backend."""
    session = {"meta": {"running_confidence": confidence}}
    assert _sse_session_severity(session) == expected


def test_normal_has_no_counselor_protocol():
    result = _build_result("anxiety", 0.44)
    assert result["severity"] == "Normal"
    assert result["counselor_protocol"] is None
    assert result["crisis_resources"] is None


@pytest.mark.parametrize("confidence", [0.45, 0.70])
def test_low_injects_the_low_counselor_protocol(confidence):
    result = _build_result("anxiety", confidence)
    assert result["severity"] == "Low"
    assert result["counselor_protocol"] == COUNSELOR_PROTOCOLS["low"]
    assert result["crisis_resources"] is None


@pytest.mark.parametrize("confidence", [0.71, 0.76])
def test_moderate_injects_the_stronger_protocol(confidence):
    result = _build_result("anxiety", confidence)
    assert result["severity"] == "Moderate"
    assert result["counselor_protocol"] == COUNSELOR_PROTOCOLS["moderate"]
    # The moderate protocol is a distinct, stronger prompt than low.
    assert result["counselor_protocol"] != COUNSELOR_PROTOCOLS["low"]
    assert result["crisis_resources"] is None


@pytest.mark.parametrize("confidence", [0.77, 0.98])
def test_high_applies_high_protocol_and_is_alertable(confidence):
    result = _build_result("anxiety", confidence)
    assert result["severity"] == "High"
    assert result["counselor_protocol"] == COUNSELOR_PROTOCOLS["high"]
    assert result["crisis_resources"] is not None
    assert should_alert_counselor(result["severity"]) is True
    assert result["severity"] in URGENT_SEVERITIES


@pytest.mark.parametrize("confidence", [0.99, 1.00])
def test_crisis_applies_crisis_protocol_and_escalates_immediately(confidence):
    result = _build_result("anxiety", confidence)
    assert result["severity"] == "Crisis"
    assert result["counselor_protocol"] == COUNSELOR_PROTOCOLS["crisis"]
    assert result["crisis_resources"] is not None
    assert should_alert_counselor(result["severity"]) is True
    assert result["severity"] in URGENT_SEVERITIES

    alert = process_alert(
        "sess-boundary-crisis",
        "u1",
        "anxiety",
        result["anxiety_score"],
        "boundary test",
        result["severity"],
    )
    assert alert["alert_sent"] is True
    assert counselor.ALERTS[0]["severity"] == "Crisis"


def test_bands_have_no_gap_or_overlap():
    """Adjacent bands meet exactly: each lower band stops one hundredth below
    the next band's inclusive start."""
    assert SEVERITY_LOW - 0.01 == 0.44
    assert SEVERITY_MODERATE - 0.01 == 0.70
    assert SEVERITY_HIGH - 0.01 == 0.76
    assert CRISIS_CONFIDENCE - 0.01 == 0.98
