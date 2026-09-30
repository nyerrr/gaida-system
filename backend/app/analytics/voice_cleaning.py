"""
Voice cleaning for the GAIDA acoustic pipeline.

Two conservative pre-processing steps applied to the raw waveform **before**
acoustic feature extraction (see `app/analytics/acoustic_features.py`):

1. **Background-noise removal** — stationary spectral gating (`noisereduce`),
   tuned conservatively (`prop_decrease=0.75`, `n_std_thresh_stationary=1.5`)
   so speech content — and therefore the jitter/shimmer/pitch statistics the
   anxiety detector relies on — is not distorted.
2. **Loudness normalization** — global RMS normalization to a fixed target
   level, so energy-based comparisons are fair across recordings, mics, and
   volumes.

Downstream feature thresholds (the pause/silence cutoff and the sad/angry
energy cutoffs in `acoustic_features._detect_emotion`) are expressed
*relative to a reference RMS* via the helpers here. With default settings the
relative thresholds map to exactly the legacy absolute values (silence `0.01`,
sad `0.02`, angry `0.08`), so disabling cleaning (`GAIDA_VOICE_CLEANING=0`)
reproduces the original raw pipeline with zero behavior change.

Config (env vars, read once at import like other backend modules):

    GAIDA_VOICE_CLEANING          master toggle              default "1" (on)
    GAIDA_NOISE_PROP_DECREASE     noise removal strength     default 0.75 (0=none, 1=full)
    GAIDA_NOISE_N_STD_THRESH      noise-gate std threshold   default 1.5
    GAIDA_VOICE_NORM_TARGET_RMS   target loudness (RMS)      default 0.05
    GAIDA_SILENCE_FRACTION        silence cutoff vs ref RMS  default 0.2
    GAIDA_SAD_ENERGY_FRACTION     sad energy cutoff vs ref   default 0.4
    GAIDA_ANGRY_ENERGY_FRACTION   angry energy cutoff vs ref default 1.6
"""

from __future__ import annotations

import os

import numpy as np

# ── Configuration (read once at import) ─────────────────────────────────────
VOICE_CLEANING_ENABLED = os.getenv("GAIDA_VOICE_CLEANING", "1").lower() in (
    "1", "true", "yes", "on",
)
NOISE_PROP_DECREASE = float(os.getenv("GAIDA_NOISE_PROP_DECREASE", "0.75"))
NOISE_N_STD_THRESH = float(os.getenv("GAIDA_NOISE_N_STD_THRESH", "1.5"))
NORM_TARGET_RMS = float(os.getenv("GAIDA_VOICE_NORM_TARGET_RMS", "0.05"))

# Downstream thresholds as fractions of the reference RMS. With the default
# NORM_TARGET_RMS=0.05 these reproduce the pre-cleaning absolute values:
# silence 0.01, sad 0.02, angry 0.08 (0.2*0.05 / 0.4*0.05 / 1.6*0.05).
SILENCE_FRACTION = float(os.getenv("GAIDA_SILENCE_FRACTION", "0.2"))
SAD_ENERGY_FRACTION = float(os.getenv("GAIDA_SAD_ENERGY_FRACTION", "0.4"))
ANGRY_ENERGY_FRACTION = float(os.getenv("GAIDA_ANGRY_ENERGY_FRACTION", "1.6"))

# Reference RMS used when cleaning is OFF — chosen so the relative thresholds
# above reduce to the legacy absolute values with no behavior change.
_LEGACY_REFERENCE_RMS = 0.05

try:
    import noisereduce as _nr  # type: ignore
    _NR_AVAILABLE = True
except Exception:  # pragma: no cover - import-failure path
    _nr = None  # type: ignore
    _NR_AVAILABLE = False
    if VOICE_CLEANING_ENABLED:
        print(
            "[voice_cleaning] WARNING: 'noisereduce' is not installed — "
            "background-noise removal is disabled (loudness normalization "
            "still applies). Add it to requirements: pip install noisereduce"
        )


def cleaning_enabled() -> bool:
    """Whether the full voice-cleaning chain (denoise + normalize) is active."""
    return VOICE_CLEANING_ENABLED


def reference_rms() -> float:
    """
    The RMS level downstream thresholds are relative to.

    When cleaning is on this is the loudness-normalization target; when off it
    is a fixed legacy reference so the original absolute thresholds survive.
    """
    if VOICE_CLEANING_ENABLED:
        return NORM_TARGET_RMS
    return _LEGACY_REFERENCE_RMS


def silence_threshold(frame_rms: np.ndarray | None = None) -> float:
    """
    Absolute RMS cutoff used by the pause/silence detector.

    Cleaning off: fixed legacy value (SILENCE_FRACTION × reference, i.e. 0.01
    at defaults). Cleaning on: the same reference value, but raised to ~1.5x
    the clip's 10th-percentile frame RMS when that is higher — so pauses that
    denoising reduced to a small residual are still recognized as silence.
    Capped at half the median frame level so a nonstop-speech clip can never
    be misread as all-silent.
    """
    base = SILENCE_FRACTION * reference_rms()
    if not VOICE_CLEANING_ENABLED or frame_rms is None or len(frame_rms) == 0:
        return base
    floor = float(np.percentile(frame_rms, 10))
    adaptive = 1.5 * (floor + 1e-12)
    cap = 0.5 * (float(np.median(frame_rms)) + 1e-12)
    return min(max(base, adaptive), max(base, cap))


def emotion_energy_thresholds() -> dict:
    """Absolute `energy_mean` cutoffs for the sad / angry emotion rules."""
    ref = reference_rms()
    return {
        "sad": SAD_ENERGY_FRACTION * ref,
        "angry": ANGRY_ENERGY_FRACTION * ref,
    }


def _frame_rms(y: np.ndarray, hop: int = 512) -> np.ndarray:
    """Per-frame RMS of a mono signal (numpy framing, no librosa needed)."""
    out = []
    for i in range(0, len(y), hop):
        seg = y[i:i + hop]
        out.append(float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0)
    return np.asarray(out)


def _noise_profile(y: np.ndarray, sr: int):
    """
    Leading room-tone to use as the noise reference, if there is one.

    Browser mic recordings typically start with a few hundred ms of background
    only (the user taps record, then speaks). Using that segment as the noise
    profile (Audacity-style) gives a much cleaner gate than noisereduce's
    default of estimating noise from the whole clip — which includes speech.

    The lead-in only counts as "quiet" when its level is close to the clip's
    10th-percentile frame RMS (the noise floor), so a recording where the user
    starts talking immediately is never misread as silence. Returns None when
    there is no reliable lead-in, which makes noisereduce fall back to
    whole-clip statistics.
    """
    n = min(int(0.30 * sr), len(y))
    if n < sr // 4:  # clip too short for a reliable lead-in
        return None
    lead = y[:n]
    lead_rms = float(np.sqrt(np.mean(lead ** 2)))
    floor = float(np.percentile(_frame_rms(y), 10)) + 1e-12
    if lead_rms < 1.5 * floor:
        return lead
    return None


def clean_voice(y: np.ndarray, sr: int) -> np.ndarray:
    """
    Denoise + normalize a mono waveform.

    Non-fatal by design: if noisereduce fails, the signal falls through to
    loudness normalization only, and if that also fails the raw signal is
    returned unchanged so the rest of the pipeline still works.
    """
    if not VOICE_CLEANING_ENABLED:
        return y
    if y is None or len(y) == 0:
        return y

    # 1) Background-noise removal (stationary spectral gating, conservative).
    if _NR_AVAILABLE:
        try:
            y = _nr.reduce_noise(
                y=np.asarray(y, dtype=np.float64),
                sr=int(sr),
                stationary=True,
                y_noise=_noise_profile(y, sr),
                prop_decrease=NOISE_PROP_DECREASE,
                n_std_thresh_stationary=NOISE_N_STD_THRESH,
                use_tqdm=False,
                n_jobs=1,
            )
        except Exception as e:  # pragma: no cover - error path
            print(f"[voice_cleaning] Noise reduction failed (non-fatal): {e}")

    # 2) Loudness normalization to a fixed RMS target.
    try:
        rms = float(np.sqrt(np.mean(y ** 2)))
        if rms > 1e-10:
            y = y * (NORM_TARGET_RMS / rms)
            y = np.clip(y, -1.0, 1.0)
    except Exception as e:  # pragma: no cover - error path
        print(f"[voice_cleaning] Normalization failed (non-fatal): {e}")

    # Keep the float32 convention librosa.load produces.
    return np.asarray(y, dtype="float32")