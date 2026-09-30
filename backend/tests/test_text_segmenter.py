import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app.services.text_segmenter import (
    split_segments,
    sentiment_polarity,
    flag_distress,
    analyze_text_segments,
)


# ── segmentation ───────────────────────────────────────────────────────────

def test_split_segments_multiple_sentences():
    segs = split_segments("First sentence. Second one! Third one?")
    assert segs == ["First sentence", "Second one", "Third one"]


def test_split_segments_single_no_punctuation():
    assert split_segments("hello world") == ["hello world"]


def test_split_segments_newline():
    assert split_segments("line one\nline two") == ["line one", "line two"]


def test_split_segments_empty():
    assert split_segments("") == []
    assert split_segments("   ") == []


# ── sentiment ──────────────────────────────────────────────────────────────

def test_sentiment_positive():
    assert sentiment_polarity("I feel happy and calm today") > 0


def test_sentiment_negative():
    assert sentiment_polarity("I feel sad and hopeless") < 0


def test_sentiment_neutral():
    assert sentiment_polarity("The sky is blue outside") == 0.0


def test_sentiment_negation_flips():
    # "not" inverts "happy" -> the segment must not read as positive.
    assert sentiment_polarity("I am not happy about it") <= 0


def test_sentiment_taglish():
    assert sentiment_polarity("pagod na ako at malungkot") < 0


def test_sentiment_empty():
    assert sentiment_polarity("") == 0.0
    assert sentiment_polarity("1234 !!!") == 0.0


def test_sentiment_bounded():
    for seg in ("happy " * 30, "sad " * 30, ""):
        s = sentiment_polarity(seg)
        assert -1.0 <= s <= 1.0


# ── distress flags ─────────────────────────────────────────────────────────

def test_flag_distress_english():
    flags = flag_distress("I feel anxious and stressed today")
    assert "anxious" in flags
    assert "stressed" in flags


def test_flag_distress_taglish():
    flags = flag_distress("kinakabahan ako sa exam")
    assert "kinakabahan" in flags


def test_flag_distress_crisis():
    flags = flag_distress("I want to kill myself")
    assert any("kill" in f for f in flags)


def test_flag_distress_none():
    assert flag_distress("I ate lunch with my friends") == []


def test_flag_distress_empty():
    assert flag_distress("") == []
    assert flag_distress(None) == []


# ── analyze_text_segments (public API) ─────────────────────────────────────

def test_analyze_segments_shape():
    out = analyze_text_segments("I feel anxious today. But I am okay now")
    assert len(out) == 2
    for entry in out:
        assert set(entry.keys()) == {"segment", "sentiment", "distress_flags"}
        assert -1.0 <= entry["sentiment"] <= 1.0
        assert isinstance(entry["distress_flags"], list)
    # first segment carries the distress cue, second one reads positive
    assert any(entry["distress_flags"] for entry in out)
    assert out[1]["sentiment"] > 0


def test_analyze_segments_empty():
    assert analyze_text_segments("") == []
    assert analyze_text_segments("   ") == []


# ── integration: attached to the interaction analysis record ───────────────

def test_finalize_turn_attaches_segments(monkeypatch):
    from app.services import intent_router

    captured = {}

    def fake_record(session_id, sender, text, analysis=None, response=None):
        if sender == "user":
            captured["analysis"] = analysis

    monkeypatch.setattr(intent_router, "record_interaction", fake_record)

    turn = {
        "session": {"meta": {}, "messages": []},
        "session_id": "seg-test",
        "intent": "stress",
        "running_confidence": 0.6,
        "anxiety_level": "low",
        "severity": "Low",
        "anxiety_score": 1,
    }
    intent_router._finalize_turn(
        turn,
        "I feel anxious. Hindi ako makatulog",
        "reply",
        "gpt",
        False,
        fire_alert=False,
    )

    segments = captured["analysis"]["segments"]
    assert len(segments) == 2
    assert any(s["distress_flags"] for s in segments)
    # The segmenter must not disturb the fields the pipeline relies on.
    assert captured["analysis"]["intent"] == "stress"
    assert captured["analysis"]["severity"] == "Low"