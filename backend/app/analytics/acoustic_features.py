import numpy as np
import librosa
import io

# ---------------------------------------------------------------------------
# Acoustic Feature Extraction
# Extracts voice features that correlate with anxiety levels.
# Used by the multimodal anxiety detection pipeline.
#
# Features extracted:
#   pitch_mean, pitch_std       - average and variation in voice pitch
#   energy_mean, energy_std     - loudness and variation
#   speech_rate                 - onsets per second (estimated)
#   pause_ratio                 - proportion of silence in the recording
#   jitter                      - pitch irregularity (anxiety indicator)
#   shimmer                     - amplitude irregularity (anxiety indicator)
#   zcr_mean                    - zero crossing rate (voice quality)
#   mfcc_1..13_mean/std         - mel-frequency cepstral coefficients
# ---------------------------------------------------------------------------


def extract_features(audio_bytes: bytes, sample_rate: int = 16000) -> dict:
    """
    Extract acoustic features from raw audio bytes.

    Args:
        audio_bytes: Raw audio data (webm, wav, mp3, etc.)
        sample_rate:  Target sample rate for analysis (default 16000 Hz)

    Returns:
        dict of acoustic features including acoustic_anxiety_score (0.0 - 1.0)
    """
    try:
        audio_buf = io.BytesIO(audio_bytes)
        y, sr = librosa.load(audio_buf, sr=sample_rate, mono=True)

        if len(y) == 0:
            return _empty_features()

        features = {}

        # ── Pitch (F0) ──────────────────────────────────────────────────────
        # High pitch variability is a clinical anxiety indicator
        f0, voiced_flag, _ = librosa.pyin(
            y,
            fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C7'),
            sr=sr
        )
        voiced_f0 = f0[voiced_flag] if f0 is not None else np.array([])
        features['pitch_mean'] = float(np.mean(voiced_f0)) if len(voiced_f0) > 0 else 0.0
        features['pitch_std']  = float(np.std(voiced_f0))  if len(voiced_f0) > 0 else 0.0

        # ── Energy (RMS) ────────────────────────────────────────────────────
        # Irregular energy levels indicate stress
        rms = librosa.feature.rms(y=y)[0]
        features['energy_mean'] = float(np.mean(rms))
        features['energy_std']  = float(np.std(rms))

        # ── Pause Detection ─────────────────────────────────────────────────
        # High pause ratio = hesitation, anxiety
        silence_threshold = 0.01
        silent_frames = np.sum(rms < silence_threshold)
        features['pause_ratio'] = float(silent_frames / len(rms)) if len(rms) > 0 else 0.0

        # ── Speech Rate ──────────────────────────────────────────────────────
        # Too fast or too slow = anxiety indicator
        onsets = librosa.onset.onset_detect(y=y, sr=sr, units='time')
        duration = librosa.get_duration(y=y, sr=sr)
        features['speech_rate'] = float(len(onsets) / duration) if duration > 0 else 0.0

        # ── Jitter (pitch irregularity) ──────────────────────────────────────
        # Voice tremor linked to anxiety and stress
        if len(voiced_f0) > 1:
            periods = 1.0 / (voiced_f0 + 1e-10)
            jitter = float(
                np.mean(np.abs(np.diff(periods))) / (np.mean(periods) + 1e-10)
            )
        else:
            jitter = 0.0
        features['jitter'] = jitter

        # ── Shimmer (amplitude irregularity) ─────────────────────────────────
        # Voice instability linked to anxiety
        if len(rms) > 1:
            shimmer = float(
                np.mean(np.abs(np.diff(rms))) / (np.mean(rms) + 1e-10)
            )
        else:
            shimmer = 0.0
        features['shimmer'] = shimmer

        # ── Zero Crossing Rate ───────────────────────────────────────────────
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        features['zcr_mean'] = float(np.mean(zcr))

        # ── MFCCs (13 coefficients) ──────────────────────────────────────────
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        for i, coef in enumerate(mfccs):
            features[f'mfcc_{i+1}_mean'] = float(np.mean(coef))
            features[f'mfcc_{i+1}_std']  = float(np.std(coef))

        # ── Final anxiety score ───────────────────────────────────────────────
        features['acoustic_anxiety_score'] = _score_from_features(features)

        return features

    except Exception as e:
        print(f"[acoustic_features] Extraction error: {e}")
        return _empty_features()


def _score_from_features(f: dict) -> float:
    """
    Compute a 0.0 to 1.0 acoustic anxiety score.
    Higher = more likely anxious.

    Based on clinical indicators from the GAIDA thesis:
    - High pitch_std (voice tremor)
    - High jitter (pitch irregularity)
    - High shimmer (amplitude irregularity)
    - High pause_ratio (hesitation)
    - Abnormal speech_rate (too fast or too slow)
    """
    score = 0.0

    if f.get('pitch_std', 0) > 30:
        score += 0.25

    if f.get('jitter', 0) > 0.02:
        score += 0.25

    if f.get('shimmer', 0) > 0.15:
        score += 0.20

    if f.get('pause_ratio', 0) > 0.40:
        score += 0.15

    rate = f.get('speech_rate', 3)
    if rate > 6 or rate < 1:
        score += 0.15

    return round(min(score, 1.0), 3)


def map_acoustic_to_severity(acoustic_score: float) -> str:
    """
    Map 0.0 - 1.0 acoustic anxiety score to Low / Moderate / High.
    Thresholds based on GAIDA classification criteria.
    """
    if acoustic_score >= 0.65:
        return "High"
    if acoustic_score >= 0.35:
        return "Moderate"
    return "Low"


def fuse_with_text_severity(
    acoustic_severity: str,
    text_severity: str
) -> str:
    """
    Combine acoustic and text severity into a final severity label.
    Takes the higher of the two to avoid missing High risk cases.

    Args:
        acoustic_severity: 'Low' | 'Moderate' | 'High' from voice
        text_severity:     'Low' | 'Moderate' | 'High' from intent_router

    Returns:
        Final fused severity label
    """
    order = {'Low': 0, 'Moderate': 1, 'High': 2}
    a = order.get(acoustic_severity, 0)
    t = order.get(text_severity, 0)
    fused = max(a, t)
    reverse = {0: 'Low', 1: 'Moderate', 2: 'High'}
    return reverse[fused]


def _empty_features() -> dict:
    """Return zeroed feature dict when extraction fails."""
    features = {
        'pitch_mean': 0.0,
        'pitch_std': 0.0,
        'energy_mean': 0.0,
        'energy_std': 0.0,
        'pause_ratio': 0.0,
        'speech_rate': 0.0,
        'jitter': 0.0,
        'shimmer': 0.0,
        'zcr_mean': 0.0,
        'acoustic_anxiety_score': 0.0,
    }
    for i in range(1, 14):
        features[f'mfcc_{i}_mean'] = 0.0
        features[f'mfcc_{i}_std']  = 0.0
    return features