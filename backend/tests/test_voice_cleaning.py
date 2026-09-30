import sys
import os
import io
import wave

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

import app.analytics.voice_cleaning as vc
from app.analytics.acoustic_features import extract_features


def _synthetic(sr=16000, seconds=2.0, seed=7):
    """Speech-like tone (0.5 s quiet lead-in + voiced periods + pauses) + noise."""
    t = np.arange(int(sr * seconds)) / sr
    rng = np.random.default_rng(seed)
    voiced = 0.15 * np.sin(2 * np.pi * 180 * t) + 0.06 * np.sin(2 * np.pi * 270 * t)
    env = np.zeros_like(t)
    env[int(0.5 * sr):int(1.6 * sr)] = 1.0
    return voiced * env + 0.01 * rng.standard_normal(t.shape)


def _wav_bytes(y, sr=16000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
    return buf.getvalue()


# ── disabled path = legacy behavior ─────────────────────────────────────────

def test_disabled_returns_identity(monkeypatch):
    monkeypatch.setattr(vc, "VOICE_CLEANING_ENABLED", False)
    y = _synthetic()
    out = vc.clean_voice(y.copy(), 16000)
    assert np.allclose(out, y, rtol=0, atol=0)  # untouched
    assert out.dtype == y.dtype


def test_disabled_thresholds_match_legacy(monkeypatch):
    # With cleaning off the relative thresholds must equal the original
    # absolute values: silence 0.01, sad 0.02, angry 0.08.
    monkeypatch.setattr(vc, "VOICE_CLEANING_ENABLED", False)
    assert vc.silence_threshold() == pytest.approx(0.01, abs=1e-12)
    cutoffs = vc.emotion_energy_thresholds()
    assert cutoffs["sad"] == pytest.approx(0.02, abs=1e-12)
    assert cutoffs["angry"] == pytest.approx(0.08, abs=1e-12)


def test_enabled_pause_threshold_adapts_to_denoised_floor(monkeypatch):
    monkeypatch.setattr(vc, "VOICE_CLEANING_ENABLED", True)
    frame_rms = np.array([0.0004] * 40 + [0.06] * 60)  # quiet floor + speech
    thr = vc.silence_threshold(frame_rms)
    assert thr >= 0.01                       # never below the reference cutoff
    assert np.sum(frame_rms < thr) >= 40     # quiet frames read as silence
    # A nonstop-speech clip must not be misread as all-silent (cap guard).
    talk_only = np.full(100, 0.10)
    assert np.sum(talk_only < vc.silence_threshold(talk_only)) == 0


# ── enabled path ────────────────────────────────────────────────────────────

def test_enabled_normalizes_gain_to_target(monkeypatch):
    monkeypatch.setattr(vc, "VOICE_CLEANING_ENABLED", True)
    monkeypatch.setattr(vc, "NORM_TARGET_RMS", 0.05)
    y = _synthetic() * 8.0  # wildly different input gain
    out = vc.clean_voice(y.copy(), 16000)
    rms = float(np.sqrt(np.mean(out ** 2)))
    assert rms == pytest.approx(0.05, rel=0.25)


@pytest.mark.skipif(not vc._NR_AVAILABLE, reason="noisereduce not installed")
def test_enabled_denoises(monkeypatch):
    monkeypatch.setattr(vc, "VOICE_CLEANING_ENABLED", True)
    sr = 16000
    t = np.arange(sr * 3) / sr
    rng = np.random.default_rng(3)
    tone = 0.2 * np.sin(2 * np.pi * 220 * t)
    env = np.zeros_like(t)
    env[int(0.5 * sr):int(1.0 * sr)] = 1.0
    env[int(1.3 * sr):int(1.9 * sr)] = 1.0
    env[int(2.2 * sr):int(2.6 * sr)] = 1.0
    clean = tone * env          # speech-like: quiet lead-in + pauses
    noisy = clean + 0.05 * rng.standard_normal(t.shape)

    def corr(a, b):
        a, b = a - a.mean(), b - b.mean()
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))

    cleaned = vc.clean_voice(noisy.copy(), sr)
    # Cleaning must pull the noisy clip closer to the clean tone (correlation
    # is scale-invariant, so the normalizer can't fake this).
    assert corr(cleaned, clean) > corr(noisy, clean) + 1e-3


def test_extract_features_runs_with_cleaning(monkeypatch):
    monkeypatch.setattr(vc, "VOICE_CLEANING_ENABLED", True)
    feats = extract_features(_wav_bytes(_synthetic()))
    for key in [
        "pitch_mean", "pitch_std", "energy_mean", "energy_std", "pause_ratio",
        "speech_rate", "duration", "jitter", "shimmer", "zcr_mean",
        "acoustic_anxiety_score", "acoustic_emotion", "acoustic_confidence",
    ]:
        assert key in feats, f"missing feature: {key}"
    assert 0.0 <= feats["acoustic_anxiety_score"] <= 1.0
    assert feats["acoustic_emotion"] in ("neutral", "anxious", "sad", "angry", "calm")


def test_empty_signal_is_safe(monkeypatch):
    monkeypatch.setattr(vc, "VOICE_CLEANING_ENABLED", True)
    out = vc.clean_voice(np.array([], dtype="float32"), 16000)
    assert out.size == 0