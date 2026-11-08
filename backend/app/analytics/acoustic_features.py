import numpy as np
import librosa
import io
import tempfile
import os
import subprocess

from app.analytics.voice_cleaning import (
    clean_voice,
    silence_threshold as voice_silence_threshold,
    emotion_energy_thresholds,
)

def _convert_to_wav(audio_bytes: bytes) -> bytes:
    """
    Convert any audio format (webm, ogg, mp3, etc.) to WAV using ffmpeg.
    Uses CapCut's bundled ffmpeg if system ffmpeg not in PATH.
    """
    import os

    # Try to find ffmpeg — system PATH first, then bundled fallbacks
    ffmpeg_cmd = "ffmpeg"
    if _is_ffmpeg_available("ffmpeg"):
        ffmpeg_cmd = "ffmpeg"
    else:
        try:
            import imageio_ffmpeg  # bundled static ffmpeg (no apt/PATH needed)
            ffmpeg_cmd = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp_in:
        tmp_in.write(audio_bytes)
        tmp_in_path = tmp_in.name

    tmp_out_path = tmp_in_path.replace(".webm", ".wav")

    try:
        subprocess.run(
            [
                ffmpeg_cmd, "-y",
                "-i", tmp_in_path,
                "-ar", "16000",
                "-ac", "1",
                "-f", "wav",
                tmp_out_path
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        with open(tmp_out_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(tmp_in_path):
            os.unlink(tmp_in_path)
        if os.path.exists(tmp_out_path):
            os.unlink(tmp_out_path)


def _is_ffmpeg_available(cmd: str) -> bool:
    """Check if ffmpeg is available in PATH."""
    try:
        subprocess.run([cmd, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def extract_features(audio_bytes: bytes, sample_rate: int = 16000, baseline: dict = None) -> dict:
    try:
        # Try direct load first
        try:
            audio_buf = io.BytesIO(audio_bytes)
            y, sr = librosa.load(audio_buf, sr=sample_rate, mono=True)
        except Exception:
            # Direct load failed — convert via ffmpeg first
            wav_bytes = _convert_to_wav(audio_bytes)
            audio_buf = io.BytesIO(wav_bytes)
            y, sr = librosa.load(audio_buf, sr=sample_rate, mono=True)

        if len(y) == 0:
            return _empty_features()

        # ── Voice cleaning: background-noise removal + loudness normalization
        y = clean_voice(y, sr)

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

        # Semitone representation (relative to A440)
        if features['pitch_mean'] > 0:
            features['pitch_semitones'] = float(12.0 * np.log2(features['pitch_mean'] / 440.0) + 69.0)
        else:
            features['pitch_semitones'] = 0.0

        # Baseline comparison if available
        if baseline and isinstance(baseline, dict) and baseline.get('pitch_mean', 0) > 0 and features['pitch_mean'] > 0:
            base_p_mean = float(baseline['pitch_mean'])
            base_p_std = max(float(baseline.get('pitch_std', 20.0)), 5.0)
            features['pitch_delta_semitones'] = float(abs(12.0 * np.log2(features['pitch_mean'] / base_p_mean)))
            features['pitch_std_ratio'] = float(features['pitch_std'] / base_p_std)
        else:
            features['pitch_delta_semitones'] = 0.0
            features['pitch_std_ratio'] = 1.0

        # ── Energy (RMS) ────────────────────────────────────────────────────
        rms = librosa.feature.rms(y=y)[0]
        features['energy_mean'] = float(np.mean(rms))
        features['energy_std']  = float(np.std(rms))

        # ── Pause Detection ─────────────────────────────────────────────────
        # Silence cutoff is relative to the (normalized) reference RMS, and
        # adapts to the denoised noise floor (see voice_cleaning).
        silence_threshold = voice_silence_threshold(np.asarray(rms))
        silent_frames = np.sum(rms < silence_threshold)
        features['pause_ratio'] = float(silent_frames / len(rms)) if len(rms) > 0 else 0.0

        # ── Speech Rate ──────────────────────────────────────────────────────
        onsets = librosa.onset.onset_detect(y=y, sr=sr, units='time')
        duration = librosa.get_duration(y=y, sr=sr)
        features['speech_rate'] = float(len(onsets) / duration) if duration > 0 else 0.0
        features['duration'] = float(duration)

        if baseline and isinstance(baseline, dict) and 'speech_rate' in baseline:
            features['rate_delta'] = float(features['speech_rate'] - baseline['speech_rate'])
        else:
            features['rate_delta'] = 0.0

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
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        features['spectral_centroid_mean'] = float(np.mean(spectral_centroid))

        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        features['spectral_rolloff_mean'] = float(np.mean(rolloff))

        # ── MFCCs (13 coefficients) ──────────────────────────────────────────
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        for i, coef in enumerate(mfccs):
            features[f'mfcc_{i+1}_mean'] = float(np.mean(coef))
            features[f'mfcc_{i+1}_std']  = float(np.std(coef))

        # ── Scores ───────────────────────────────────────────────────────────
        features['acoustic_anxiety_score'] = _score_from_features(features, baseline=baseline)
        features['acoustic_emotion'] = _detect_emotion(features)

        # ── Confidence Estimation ─────────────────────────────────────────────
        # Confidence reflects sample duration, speech presence, and score intensity
        if duration < 0.8:
            conf = min(0.35, duration / 2.0)
        else:
            dur_factor = min(1.0, duration / 2.5)
            conf = dur_factor * (0.45 + 0.55 * min(features['acoustic_anxiety_score'] * 1.2, 1.0))

        if len(voiced_f0) < 5 and duration >= 0.8:
            conf *= 0.5

        features['acoustic_confidence'] = round(float(min(1.0, max(0.1, conf))), 3)

        return features

    except Exception as e:
        print(f"[acoustic_features] Extraction error: {e}")
        return _empty_features()


def _score_from_features(f: dict, baseline: dict = None) -> float:
    score = 0.0
    weights = 0.0

    # 1. Pitch Instability (weight: 0.25)
    pitch_std = f.get('pitch_std', 0.0)
    std_ratio = f.get('pitch_std_ratio', 1.0)
    pitch_delta_st = f.get('pitch_delta_semitones', 0.0)

    if baseline and std_ratio > 0:
        pitch_score = min(max(std_ratio - 0.8, 0.0) / 1.5, 1.0) * 0.7 + min(pitch_delta_st / 3.5, 1.0) * 0.3
    else:
        pitch_score = min(pitch_std / 70.0, 1.0) if pitch_std > 0 else 0.0

    score += pitch_score * 0.25
    weights += 0.25

    # 2. Jitter / Vocal Micro-tremor (weight: 0.25)
    # Healthy voice jitter is < 0.01; stressed vocal fold tension is >= 0.02
    jitter = f.get('jitter', 0.0)
    jitter_score = min(max(jitter - 0.005, 0.0) / 0.035, 1.0) if jitter > 0 else 0.0
    score += jitter_score * 0.25
    weights += 0.25

    # 3. Shimmer / Amplitude Perturbation (weight: 0.20)
    # Strained/breathy amplitude perturbation is >= 0.15
    shimmer = f.get('shimmer', 0.0)
    shimmer_score = min(max(shimmer - 0.05, 0.0) / 0.22, 1.0) if shimmer > 0 else 0.0
    score += shimmer_score * 0.20
    weights += 0.20

    # 4. Pause Detection / Hesitations (weight: 0.15)
    pause_ratio = f.get('pause_ratio', 0.0)
    pause_score = min(max(pause_ratio - 0.15, 0.0) / 0.40, 1.0)
    score += pause_score * 0.15
    weights += 0.15

    # 5. Speech Rate (weight: 0.15)
    # Agitated/pressured: > 5.5 onsets/sec. Hesitant/frozen: < 1.8 onsets/sec.
    rate = f.get('speech_rate', 3.0)
    if rate > 5.5:
        rate_score = min((rate - 5.5) / 3.5, 1.0)
    elif 0.1 < rate < 1.8:
        rate_score = min((1.8 - rate) / 1.5, 1.0)
    else:
        rate_score = 0.0
    score += rate_score * 0.15
    weights += 0.15

    raw_score = score / weights if weights > 0 else 0.0

    # ── High-Arousal Control Discrimination ──────────────────────────────
    # Distinguish controlled, confident/angry fast speech from anxious speech:
    # If speech is fast and continuous, but jitter is low and pauses are absent,
    # the speaker exhibits strong neuromuscular vocal control.
    is_controlled_assertive = (
        rate > 5.2 and jitter < 0.015 and pause_ratio < 0.18
    )
    if is_controlled_assertive:
        raw_score *= 0.60  # discount: controlled rapid speech is not acute anxiety

    # If active vocal tremor is detected (elevated jitter AND shimmer), boost score
    has_vocal_tremor = (jitter >= 0.020 and shimmer >= 0.15)
    if has_vocal_tremor and raw_score > 0.20:
        raw_score = min(1.0, raw_score + 0.10)

    return round(min(max(raw_score, 0.0), 1.0), 3)


def _detect_emotion(f: dict) -> str:
    pitch_mean  = f.get('pitch_mean', 0)
    pitch_std   = f.get('pitch_std', 0)
    energy_mean = f.get('energy_mean', 0)
    speech_rate = f.get('speech_rate', 3)
    pause_ratio = f.get('pause_ratio', 0)
    jitter      = f.get('jitter', 0)
    shimmer     = f.get('shimmer', 0)

    scores = {'anxious': 0.0, 'sad': 0.0, 'angry': 0.0, 'calm': 0.0}
    energy_cutoffs = emotion_energy_thresholds()

    # ANXIOUS: pitch instability, vocal tremor (jitter/shimmer), hesitations or erratic rate
    if pitch_std > 28:
        scores['anxious'] += 0.25
    if jitter > 0.020:
        scores['anxious'] += 0.25
    if shimmer > 0.15:
        scores['anxious'] += 0.20
    if pause_ratio > 0.30:
        scores['anxious'] += 0.20
    if speech_rate > 5.2 and (jitter > 0.018 or pause_ratio > 0.22):
        scores['anxious'] += 0.20
    elif 0.1 < speech_rate < 1.8 and pause_ratio > 0.35:
        scores['anxious'] += 0.15

    # SAD: low pitch, slow speech, quiet energy, high pause ratio
    if 0 < pitch_mean < 155:
        scores['sad'] += 0.30
    if 0.1 < speech_rate < 2.2:
        scores['sad'] += 0.30
    if pause_ratio > 0.45:
        scores['sad'] += 0.25
    if energy_mean < energy_cutoffs['sad']:
        scores['sad'] += 0.20

    # ANGRY: high energy, high pitch, high speech rate, low pauses, but CONTROLLED jitter
    if energy_mean > energy_cutoffs['angry']:
        scores['angry'] += 0.35
    if pitch_mean > 240:
        scores['angry'] += 0.25
    if speech_rate > 5.5:
        scores['angry'] += 0.25
    if pause_ratio < 0.15:
        scores['angry'] += 0.20
    if jitter < 0.018:
        scores['angry'] += 0.15

    # CALM: steady pitch, moderate tempo, low jitter, natural pauses
    if 1.8 <= speech_rate <= 4.6:
        scores['calm'] += 0.30
    if 0 < pitch_std < 22:
        scores['calm'] += 0.30
    if 0 < jitter < 0.012:
        scores['calm'] += 0.25
    if 0.08 <= pause_ratio <= 0.30:
        scores['calm'] += 0.20

    best = max(scores, key=scores.get)
    if scores[best] < 0.25:
        return 'neutral'
    return best


def map_acoustic_to_severity(acoustic_score: float) -> str:
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
    acoustic_confidence: float = 1.0,
) -> str:
    order = {'Normal': 0, 'Low': 1, 'Moderate': 2, 'High': 3}
    reverse = {0: 'Normal', 1: 'Low', 2: 'Moderate', 3: 'High'}

    a = order.get(acoustic_severity, 0)
    t = order.get(text_severity, 0)

    # If acoustic confidence is low (< 0.45), trust text only
    if acoustic_confidence < 0.45:
        return text_severity if text_severity in order else reverse[t]

    fused = t

    # If acoustic indicates higher distress than text:
    if a > t:
        if acoustic_emotion in ('anxious', 'sad'):
            if acoustic_confidence >= 0.75:
                # Strong acoustic confidence: can upgrade up to 2 tiers (e.g. Normal -> Moderate)
                fused = min(a, t + 2)
            else:
                # Moderate acoustic confidence: conservative single tier upgrade
                fused = min(a, t + 1)
    else:
        fused = t

    # If text is Normal but voice indicates anxious/sad emotion with solid confidence, bump to Low
    if fused == 0 and acoustic_emotion in ('anxious', 'sad') and acoustic_confidence >= 0.50:
        fused = 1

    # Safety guard: acoustic analysis alone NEVER escalates to Crisis
    fused = min(fused, 3)

    return reverse.get(fused, 'Normal')


def _empty_features() -> dict:
    features = {
        'pitch_mean': 0.0, 'pitch_std': 0.0,
        'energy_mean': 0.0, 'energy_std': 0.0,
        'pause_ratio': 0.0, 'speech_rate': 0.0,
        'duration': 0.0, 'jitter': 0.0, 'shimmer': 0.0,
        'zcr_mean': 0.0, 'spectral_centroid_mean': 0.0,
        'spectral_rolloff_mean': 0.0,
        'pitch_semitones': 0.0,
        'pitch_delta_semitones': 0.0,
        'pitch_std_ratio': 1.0,
        'rate_delta': 0.0,
        'acoustic_anxiety_score': 0.0,
        'acoustic_emotion': 'neutral',
        'acoustic_confidence': 0.0,
    }
    for i in range(1, 14):
        features[f'mfcc_{i}_mean'] = 0.0
        features[f'mfcc_{i}_std']  = 0.0
    return features

def log_to_supabase(session_id: str, features: dict) -> bool:
    """
    Persist extracted acoustic features + severity to Supabase.
    Call this right after extract_features() in your voice route.

    Returns True on success, False on failure.
    """
    try:
        from app.database.database import supabase
        from datetime import datetime, timezone

        severity = map_acoustic_to_severity(
            features.get("acoustic_anxiety_score", 0.0)
        )

        row = {
            "session_id":              session_id,
            "timestamp":               datetime.now(timezone.utc).isoformat(),
            "duration":                features.get("duration"),
            "pitch_mean":              features.get("pitch_mean"),
            "pitch_std":               features.get("pitch_std"),
            "energy_mean":             features.get("energy_mean"),
            "energy_std":              features.get("energy_std"),
            "pause_ratio":             features.get("pause_ratio"),
            "speech_rate":             features.get("speech_rate"),
            "jitter":                  features.get("jitter"),
            "shimmer":                 features.get("shimmer"),
            "zcr_mean":                features.get("zcr_mean"),
            "spectral_centroid_mean":  features.get("spectral_centroid_mean"),
            "spectral_rolloff_mean":   features.get("spectral_rolloff_mean"),
            "acoustic_anxiety_score":  features.get("acoustic_anxiety_score"),
            "acoustic_emotion":        features.get("acoustic_emotion"),
            "acoustic_confidence":     features.get("acoustic_confidence"),
            "severity":                severity,
        }

        # Add all 13 MFCCs
        for i in range(1, 14):
            row[f"mfcc_{i}_mean"] = features.get(f"mfcc_{i}_mean")
            row[f"mfcc_{i}_std"]  = features.get(f"mfcc_{i}_std")

        supabase.table("acoustic_logs").insert(row).execute()
        return True

    except Exception as e:
        print(f"[acoustic_features] Supabase log error: {e}")
        return False