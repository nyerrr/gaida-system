"""
A/B validation for the GAIDA voice-cleaning step.

Compares acoustic features extracted from:
  (a) noisy audio          — cleaning OFF (raw pipeline),
  (b) the same audio       — cleaning ON  (denoise + normalize),
  (c) a clean reference    — cleaning ON, when available.

Use this to sanity-check that cleaning pulls a noisy clip back toward the
clean baseline WITHOUT distorting it into a false stress read (i.e. jitter /
shimmer / pitch must not lift the acoustic_anxiety_score on clean speech).

Usage (from backend/):

    python tools/validate_voice_cleaning.py                  # synthetic audio
    python tools/validate_voice_cleaning.py clip.wav         # a real recording

Exit code 0 on success, 1 if the noisy clip's anxiety score moves *up* after
cleaning (potential false-stress artifact worth investigating).
"""

import io
import os
import sys
import wave

import numpy as np

# Wide glyphs (═, Δ) crash on legacy cp1252 consoles; force UTF-8 output.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.analytics.voice_cleaning as vc  # noqa: E402
from app.analytics import acoustic_features as af  # noqa: E402

COMPARE_KEYS = [
    "energy_mean", "energy_std", "zcr_mean", "pause_ratio",
    "spectral_centroid_mean", "jitter", "shimmer", "speech_rate",
    "acoustic_anxiety_score",
]


def _synth_audio(sr=16000, seconds=3.0, noise_amp=0.06, seed=11):
    """Speech-like voiced tone with a quiet lead-in + silences + background noise."""
    t = np.arange(int(sr * seconds)) / sr
    rng = np.random.default_rng(seed)
    voiced = (
        0.14 * np.sin(2 * np.pi * 165 * t)
        + 0.06 * np.sin(2 * np.pi * 233 * t)
        + 0.03 * np.sin(2 * np.pi * 349 * t)
    )
    env = np.zeros_like(t)
    env[int(0.5 * sr):int(1.2 * sr)] = 1.0
    env[int(1.4 * sr):int(2.1 * sr)] = 0.9
    env[int(2.4 * sr):int(2.9 * sr)] = 0.7
    clean = voiced * env
    noisy = clean + noise_amp * rng.standard_normal(t.shape)
    return clean, noisy


def _wav_bytes(y, sr=16000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
    return buf.getvalue()


def _features(audio_bytes, cleaning_on):
    # Env vars are read at import; flip the module flag at runtime instead.
    vc.VOICE_CLEANING_ENABLED = cleaning_on
    return af.extract_features(audio_bytes)


def _fmt(v):
    if isinstance(v, float):
        return f"{v:+.4f}" if v < 0 else f" {v:+.4f}"
    return str(v)


def main():
    real_path = sys.argv[1] if len(sys.argv) > 1 else None

    if real_path and os.path.exists(real_path):
        with open(real_path, "rb") as f:
            audio_bytes = f.read()
        clean_label = "(n/a — no clean reference for a real file)"
    else:
        clean, noisy = _synth_audio()
        audio_bytes = _wav_bytes(noisy)
        clean_label = "synthetic"

    print("═" * 82)
    print(f"  VOICE-CLEANING A/B VALIDATION — {real_path or 'synthetic noisy clip'}")
    print("═" * 82)

    off = _features(audio_bytes, cleaning_on=False)
    on = _features(audio_bytes, cleaning_on=True)
    clean_ref = _features(_wav_bytes(_synth_audio()[0]), cleaning_on=True) if not real_path else {}

    print()
    print(f"{'feature':<26}{'noisy/raw':>14}{'cleaned':>14}{'clean-ref':>14}{'Δ (on-off)':>12}")
    print("-" * 82)
    for k in COMPARE_KEYS:
        off_v = off.get(k, 0.0)
        on_v = on.get(k, 0.0)
        ref_v = clean_ref.get(k, 0.0) if clean_ref else float("nan")
        delta = on_v - off_v
        print(f"{k:<26}{off_v:>14.4f}{on_v:>14.4f}{ref_v:>14.4f}{delta:>+12.4f}")

    print("-" * 82)
    print(
        f"{'emotion':<26}{off.get('acoustic_emotion'):>14}"
        f"{on.get('acoustic_emotion'):>14}{clean_ref.get('acoustic_emotion', '—'):>14}"
    )
    print(
        f"{'severity':<26}{af.map_acoustic_to_severity(off.get('acoustic_anxiety_score', 0)):>14}"
        f"{af.map_acoustic_to_severity(on.get('acoustic_anxiety_score', 0)):>14}"
        f"{af.map_acoustic_to_severity(clean_ref.get('acoustic_anxiety_score', 0)) if clean_ref else '—':>14}"
    )
    print()

    # Safety check: cleaning must not push the noisy clip's stress read UP.
    off_score = off.get("acoustic_anxiety_score", 0.0)
    on_score = on.get("acoustic_anxiety_score", 0.0)
    if on_score > off_score + 0.05:
        print(f"  ⚠️  Cleaning raised the anxiety score {off_score:.3f} → {on_score:.3f}.")
        print("     Investigate (denoising artifacts) before trusting this preset.\n")
        return 1
    print(f"  ✅ Cleaning did not inflate the stress read: {off_score:.3f} → {on_score:.3f}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())