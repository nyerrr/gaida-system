import numpy as np
import librosa
import io

def extract_features(audio_bytes: bytes, sample_rate: int = 16000) -> dict:
    try:
        audio_buf = io.BytesIO(audio_bytes)
        y, sr = librosa.load(audio_buf, sr=sample_rate, mono=True)

        if len(y) == 0:
            return _empty_features()

        features = {}

        # ── Pitch (F0) ──────────────────────────────────────────────────────
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
        rms = librosa.feature.rms(y=y)[0]
        features['energy_mean'] = float(np.mean(rms))
        features['energy_std']  = float(np.std(rms))

        # ── Pause Detection ─────────────────────────────────────────────────
        silence_threshold = 0.01
        silent_frames = np.sum(rms < silence_threshold)
        features['pause_ratio'] = float(silent_frames / len(rms)) if len(rms) > 0 else 0.0

        # ── Speech Rate ──────────────────────────────────────────────────────
        onsets = librosa.onset.onset_detect(y=y, sr=sr, units='time')
        duration = librosa.get_duration(y=y, sr=sr)
        features['speech_rate'] = float(len(onsets) / duration) if duration > 0 else 0.0
        features['duration'] = float(duration)

        # ── Jitter ──────────────────────────────────────────────────────────
        if len(voiced_f0) > 1:
            periods = 1.0 / (voiced_f0 + 1e-10)
            jitter = float(
                np.mean(np.abs(np.diff(periods))) / (np.mean(periods) + 1e-10)
            )
        else:
            jitter = 0.0
        features['jitter'] = jitter

        # ── Shimmer ──────────────────────────────────────────────────────────
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

        # ── Spectral Features ────────────────────────────────────────────────
        # Spectral centroid — brighter voice = more energy/arousal
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        features['spectral_centroid_mean'] = float(np.mean(spectral_centroid))

        # Spectral rolloff — how much energy is in higher frequencies
        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        features['spectral_rolloff_mean'] = float(np.mean(rolloff))

        # ── MFCCs (13 coefficients) ──────────────────────────────────────────
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        for i, coef in enumerate(mfccs):
            features[f'mfcc_{i+1}_mean'] = float(np.mean(coef))
            features[f'mfcc_{i+1}_std']  = float(np.std(coef))

        # ── Scores ───────────────────────────────────────────────────────────
        features['acoustic_anxiety_score'] = _score_from_features(features)
        features['acoustic_emotion'] = _detect_emotion(features)

        return features

    except Exception as e:
        print(f"[acoustic_features] Extraction error: {e}")
        return _empty_features()


def _score_from_features(f: dict) -> float:
    """
    Compute a 0.0 to 1.0 acoustic anxiety score.
    Uses weighted scoring instead of binary thresholds.
    """
    score = 0.0
    weights = 0.0

    # Pitch variability — high std = voice tremor = anxiety
    pitch_std = f.get('pitch_std', 0)
    if pitch_std > 0:
        pitch_score = min(pitch_std / 80.0, 1.0)  # normalize to 0-1
        score += pitch_score * 0.25
        weights += 0.25

    # Jitter — pitch irregularity
    jitter = f.get('jitter', 0)
    if jitter > 0:
        jitter_score = min(jitter / 0.05, 1.0)
        score += jitter_score * 0.25
        weights += 0.25

    # Shimmer — amplitude irregularity
    shimmer = f.get('shimmer', 0)
    if shimmer > 0:
        shimmer_score = min(shimmer / 0.30, 1.0)
        score += shimmer_score * 0.20
        weights += 0.20

    # Pause ratio — high pauses = hesitation/anxiety
    pause_ratio = f.get('pause_ratio', 0)
    pause_score = min(pause_ratio / 0.60, 1.0)
    score += pause_score * 0.15
    weights += 0.15

    # Speech rate — too fast or too slow = anxiety/sadness
    rate = f.get('speech_rate', 3)
    if rate > 6:
        rate_score = min((rate - 6) / 4.0, 1.0)   # too fast = anxiety
    elif rate < 1.5:
        rate_score = min((1.5 - rate) / 1.5, 1.0)  # too slow = sadness/depression
    else:
        rate_score = 0.0
    score += rate_score * 0.15
    weights += 0.15

    # Normalize by weights used
    if weights > 0:
        score = score / weights * (weights / 1.0)

    return round(min(score, 1.0), 3)


def _detect_emotion(f: dict) -> str:
    """
    Map acoustic features to an emotional state.
    Returns: 'anxious' | 'sad' | 'angry' | 'calm' | 'neutral'

    Based on:
    - Anxious: high pitch, high speech rate, high jitter, high shimmer
    - Sad: low pitch, slow speech rate, high pause ratio, low energy
    - Angry: high energy, high pitch, fast speech, low pause ratio
    - Calm: normal pitch, normal rate, low jitter/shimmer
    """
    pitch_mean  = f.get('pitch_mean', 0)
    pitch_std   = f.get('pitch_std', 0)
    energy_mean = f.get('energy_mean', 0)
    speech_rate = f.get('speech_rate', 3)
    pause_ratio = f.get('pause_ratio', 0)
    jitter      = f.get('jitter', 0)
    shimmer     = f.get('shimmer', 0)

    scores = {
        'anxious': 0.0,
        'sad':     0.0,
        'angry':   0.0,
        'calm':    0.0,
    }

    # Anxious indicators
    if pitch_std > 30:       scores['anxious'] += 0.3
    if speech_rate > 5:      scores['anxious'] += 0.25
    if jitter > 0.02:        scores['anxious'] += 0.25
    if shimmer > 0.15:       scores['anxious'] += 0.20

    # Sad indicators
    if pitch_mean < 150:     scores['sad'] += 0.3
    if speech_rate < 2:      scores['sad'] += 0.3
    if pause_ratio > 0.5:    scores['sad'] += 0.25
    if energy_mean < 0.02:   scores['sad'] += 0.15

    # Angry indicators
    if energy_mean > 0.08:   scores['angry'] += 0.3
    if pitch_mean > 250:     scores['angry'] += 0.25
    if speech_rate > 6:      scores['angry'] += 0.25
    if pause_ratio < 0.1:    scores['angry'] += 0.20

    # Calm indicators
    if 1.5 <= speech_rate <= 4.5: scores['calm'] += 0.3
    if pitch_std < 20:            scores['calm'] += 0.3
    if jitter < 0.01:             scores['calm'] += 0.2
    if 0.1 <= pause_ratio <= 0.3: scores['calm'] += 0.2

    best = max(scores, key=scores.get)

    # Only return emotion if score is meaningful
    if scores[best] < 0.2:
        return 'neutral'

    return best


def map_acoustic_to_severity(acoustic_score: float) -> str:
    """
    Map 0.0 - 1.0 acoustic anxiety score to Normal / Low / Moderate / High.
    Added Normal to match text intent severity system.
    """
    if acoustic_score >= 0.65:
        return "High"
    if acoustic_score >= 0.35:
        return "Moderate"
    if acoustic_score >= 0.15:
        return "Low"
    return "Normal"


def fuse_with_text_severity(
    acoustic_severity: str,
    text_severity: str,
    acoustic_emotion: str = None,
) -> str:
    """
    Combine acoustic and text severity into a final severity label.
    Takes the higher of the two to avoid missing high risk cases.

    If acoustic emotion is 'sad' or 'anxious' and text is Normal,
    bump up to Low as a safety net.
    """
    order = {'Normal': 0, 'Low': 1, 'Moderate': 2, 'High': 3}
    reverse = {0: 'Normal', 1: 'Low', 2: 'Moderate', 3: 'High'}

    a = order.get(acoustic_severity, 0)
    t = order.get(text_severity, 0)
    fused = max(a, t)

    # Safety net — if voice sounds sad/anxious but text is neutral, bump to Low
    if acoustic_emotion in ('sad', 'anxious') and fused == 0:
        fused = 1

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
        'duration': 0.0,
        'jitter': 0.0,
        'shimmer': 0.0,
        'zcr_mean': 0.0,
        'spectral_centroid_mean': 0.0,
        'spectral_rolloff_mean': 0.0,
        'acoustic_anxiety_score': 0.0,
        'acoustic_emotion': 'neutral',
    }
    for i in range(1, 14):
        features[f'mfcc_{i}_mean'] = 0.0
        features[f'mfcc_{i}_std']  = 0.0
    return features