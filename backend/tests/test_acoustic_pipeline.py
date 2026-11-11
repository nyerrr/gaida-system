import sys
import os
import io
import wave
import numpy as np
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.analytics.acoustic_features import (
    extract_features,
    map_acoustic_to_severity,
    fuse_with_text_severity,
    _score_from_features,
    _detect_emotion,
)


def _make_wav(sr=16000, seconds=2.0, f0=180.0, jitter_amt=0.0, shimmer_amt=0.0, pause_ratio=0.1):
    """Generate synthetic voice-like WAV bytes with controlled parameters."""
    t = np.arange(int(sr * seconds)) / sr
    # Base tone
    phase = 2 * np.pi * f0 * t
    if jitter_amt > 0:
        # Micro-tremor frequency modulation
        phase += jitter_amt * np.sin(2 * np.pi * 35 * t)
    
    signal = 0.20 * np.sin(phase) + 0.08 * np.sin(2 * phase)
    
    if shimmer_amt > 0:
        # Amplitude modulation
        signal *= (1.0 + shimmer_amt * np.sin(2 * np.pi * 15 * t))
        
    # Apply envelope for pauses
    env = np.ones_like(t)
    if pause_ratio > 0.3:
        # Insert silent gaps
        env[int(0.6 * sr):int(1.2 * sr)] = 0.0
    signal *= env

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(signal, -1, 1) * 32767).astype(np.int16).tobytes())
    return buf.getvalue()


def test_extract_features_with_baseline():
    """Verify extract_features calculates semitones and baseline deltas."""
    wav = _make_wav(seconds=2.0, f0=220.0)
    baseline = {
        "pitch_mean": 180.0,
        "pitch_std": 15.0,
        "speech_rate": 3.0,
    }
    feats = extract_features(wav, baseline=baseline)

    assert "pitch_semitones" in feats
    assert "pitch_delta_semitones" in feats
    assert "pitch_std_ratio" in feats
    assert "rate_delta" in feats
    assert feats["pitch_semitones"] > 0
    # Pitch shifted from 180 to ~220 -> delta semitones should be > 0
    assert feats["pitch_delta_semitones"] > 1.0


def test_extract_features_calculates_jitter_and_shimmer():
    """Live extraction should measure perturbation, not return placeholder zeros."""
    steady = extract_features(_make_wav(seconds=2.0, f0=180.0))
    tremulous = extract_features(
        _make_wav(seconds=2.0, f0=180.0, jitter_amt=0.05, shimmer_amt=0.3)
    )

    assert steady["jitter"] >= 0.0
    assert steady["shimmer"] >= 0.0
    assert tremulous["jitter"] > steady["jitter"]
    assert tremulous["shimmer"] > steady["shimmer"]
    assert tremulous["jitter"] > 0.0
    assert tremulous["shimmer"] > 0.0


def test_high_arousal_discrimination():
    """Verify controlled rapid speech (anger/excitement) is differentiated from anxious speech."""
    # 1. Assertive/angry speech: fast, loud, low jitter, low pauses
    angry_feats = {
        "pitch_mean": 260.0,
        "pitch_std": 35.0,
        "energy_mean": 0.09,
        "speech_rate": 6.0,
        "pause_ratio": 0.08,
        "jitter": 0.008,
        "shimmer": 0.09,
    }
    angry_score = _score_from_features(angry_feats)
    angry_emotion = _detect_emotion(angry_feats)

    # 2. Anxious speech: fast, trembling (elevated jitter/shimmer), hesitations
    anxious_feats = {
        "pitch_mean": 260.0,
        "pitch_std": 35.0,
        "energy_mean": 0.06,
        "speech_rate": 5.5,
        "pause_ratio": 0.32,
        "jitter": 0.026,
        "shimmer": 0.18,
    }
    anxious_score = _score_from_features(anxious_feats)
    anxious_emotion = _detect_emotion(anxious_feats)

    assert angry_emotion == "angry"
    assert anxious_emotion == "anxious"
    # Anxious score must be higher than assertive angry score due to tremor penalty/boosts
    assert anxious_score > angry_score


def test_calm_speech_detection():
    """Verify calm voice with steady pitch and low jitter is detected as calm."""
    calm_feats = {
        "pitch_mean": 190.0,
        "pitch_std": 14.0,
        "energy_mean": 0.04,
        "speech_rate": 3.2,
        "pause_ratio": 0.18,
        "jitter": 0.007,
        "shimmer": 0.06,
    }
    assert _detect_emotion(calm_feats) == "calm"
    score = _score_from_features(calm_feats)
    assert score < 0.20
    assert map_acoustic_to_severity(score) in ("Normal", "Low")


def test_fuse_with_text_severity_confidence_guard():
    """Low acoustic confidence should not escalate text severity."""
    # Text is Normal, Voice is High, but confidence is low (e.g. 0.30)
    fused = fuse_with_text_severity(
        acoustic_severity="High",
        text_severity="Normal",
        acoustic_emotion="anxious",
        acoustic_confidence=0.30,
    )
    assert fused == "Normal", "Low confidence voice should not upgrade text severity"


def test_fuse_with_text_severity_escalation():
    """A clear anxious voice estimate is primary for emotional severity."""
    fused = fuse_with_text_severity(
        acoustic_severity="High",
        text_severity="Normal",
        acoustic_emotion="anxious",
        acoustic_confidence=0.85,
    )
    assert fused == "High"


def test_fuse_text_can_raise_voice_severity():
    fused = fuse_with_text_severity(
        acoustic_severity="Low",
        text_severity="High",
        acoustic_emotion="anxious",
        acoustic_confidence=0.85,
    )
    assert fused == "High"


def test_fuse_preserves_text_crisis():
    fused = fuse_with_text_severity(
        acoustic_severity="Normal",
        text_severity="Crisis",
        acoustic_emotion="calm",
        acoustic_confidence=1.0,
    )
    assert fused == "Crisis"


def test_non_anxious_voice_does_not_raise_anxiety_severity():
    fused = fuse_with_text_severity(
        acoustic_severity="High",
        text_severity="Normal",
        acoustic_emotion="angry",
        acoustic_confidence=0.95,
    )
    assert fused == "Normal"


def test_fuse_with_text_never_escalates_to_crisis():
    """Acoustic features alone should never escalate a session to Crisis."""
    fused = fuse_with_text_severity(
        acoustic_severity="High",
        text_severity="Moderate",
        acoustic_emotion="anxious",
        acoustic_confidence=1.0,
    )
    assert fused in ("Moderate", "High")
    assert fused != "Crisis", "Acoustic fusion must never produce Crisis without semantic confirmation"


def test_short_duration_confidence():
    """Very short clips (< 0.8s) should have discounted confidence."""
    short_wav = _make_wav(seconds=0.5, f0=200.0)
    feats = extract_features(short_wav)
    assert feats["duration"] < 0.8
    assert feats["acoustic_confidence"] <= 0.35
