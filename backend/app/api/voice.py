import asyncio
import os
from openai import OpenAI
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from fastapi.responses import Response
from app.utils.auth import get_current_user
from app.services.tts import text_to_speech_bytes
from app.analytics.acoustic_features import (
    extract_features,
    map_acoustic_to_severity,
    fuse_with_text_severity,
    log_to_supabase,
)
from app.services.session_manager import get_session, start_session

router = APIRouter(prefix="/audio", tags=["audio"])

# ── Hosted transcription (OpenAI) — no local model, runs on fast GPUs ──
_STT_MODEL = os.getenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")
_openai_client = None


def _get_voice_client():
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai_client

@router.post("/speech-to-text")
async def speech_to_text(
    audio: UploadFile = File(...),
    session_id: str = Form(None),
    user: dict = Depends(get_current_user),
):
    try:
        if session_id:
            session = get_session(session_id)
            if session and session.get("user_id") and session["user_id"] != user["user_id"]:
                raise HTTPException(status_code=403, detail="Session does not belong to this user")
        else:
            session_id = start_session()
            session = get_session(session_id)

        # Accept any audio content type — browser sends various formats
        content_type = audio.content_type or ""
        if content_type and not content_type.startswith("audio/") and not content_type.startswith("video/webm"):
            raise HTTPException(status_code=400, detail=f"File must be audio type. Got: {content_type}")

        audio_bytes = await audio.read()

        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file.")

        # Derive extension from content type / filename
        _EXT_BY_CONTENT_TYPE = {
            "audio/webm": "webm",
            "audio/mp4": "mp4",
            "audio/aac": "aac",
            "audio/ogg": "ogg",
            "audio/wav": "wav",
            "audio/mpeg": "mp3",
        }
        upload_name = (audio.filename or "").lower()
        if "." in upload_name:
            ext = upload_name.rsplit(".", 1)[-1]
        else:
            base_type = content_type.split(";")[0].strip().lower()
            ext = _EXT_BY_CONTENT_TYPE.get(base_type, "webm")
        suffix = f".{ext}"

        # Fetch baseline from session if available
        baseline = None
        if session and "meta" in session:
            baseline = session["meta"].get("acoustic_baseline")

        # ── Concurrently run Feature Extraction & STT Transcription ──────────
        async def _extract():
            try:
                return await asyncio.to_thread(extract_features, audio_bytes, baseline=baseline)
            except Exception as e:
                print(f"[voice] Acoustic feature extraction error: {e}")
                return {}

        async def _transcribe():
            try:
                result = await asyncio.to_thread(
                    _get_voice_client().audio.transcriptions.create,
                    model=_STT_MODEL,
                    file=(f"audio{suffix}", audio_bytes),
                )
                return getattr(result, "text", "").strip()
            except Exception as e:
                print(f"[voice] Transcription error: {e}")
                raise HTTPException(status_code=500, detail="Transcription failed") from None

        acoustic_result, transcription_result = await asyncio.gather(
            _extract(), _transcribe(), return_exceptions=True
        )
        if isinstance(acoustic_result, Exception):
            print(f"[voice] Acoustic feature extraction failed: {acoustic_result}")
            acoustic_features_dict = {}
        else:
            acoustic_features_dict = acoustic_result

        acoustic_severity = map_acoustic_to_severity(
            acoustic_features_dict.get("acoustic_anxiety_score", 0.0)
        )
        acoustic_confidence = acoustic_features_dict.get("acoustic_confidence", 0.0)
        acoustic_emotion = acoustic_features_dict.get("acoustic_emotion", "neutral")

        # ── Log to Supabase ──────────────────────────────────────────────────
        acoustic_log_saved = False
        if acoustic_features_dict:
            try:
                # Supabase's client is synchronous; keep its network request off
                # the event loop. Log even when speech-to-text failed so a
                # provider outage cannot silently discard acoustic data.
                acoustic_log_saved = bool(await asyncio.to_thread(
                    log_to_supabase,
                    session_id=session_id or "unknown",
                    features=acoustic_features_dict,
                ))
            except Exception as e:
                print(f"[voice] Acoustic database write failed: {e}")

        if isinstance(transcription_result, Exception):
            if isinstance(transcription_result, HTTPException):
                raise transcription_result
            print(f"[voice] Transcription failed: {transcription_result}")
            raise HTTPException(status_code=500, detail="Transcription failed") from None
        transcript = transcription_result

        # ── Update Session State & Baseline ──────────────────────────────────
        if session:
            if "meta" not in session:
                session["meta"] = {}

            # Adaptive baseline calibration during low-stress turns
            dur = acoustic_features_dict.get("duration", 0.0)
            p_mean = acoustic_features_dict.get("pitch_mean", 0.0)
            if dur >= 1.2 and p_mean > 0 and acoustic_severity in ("Normal", "Low"):
                old_base = session["meta"].get("acoustic_baseline") or {}
                turn = session["meta"].get("acoustic_turn_count", 0)
                alpha = 1.0 / (turn + 1) if turn < 4 else 0.2

                cur_p_std = max(acoustic_features_dict.get("pitch_std", 15.0), 5.0)
                cur_rate = max(acoustic_features_dict.get("speech_rate", 3.0), 0.5)

                new_p_mean = (1 - alpha) * old_base.get("pitch_mean", p_mean) + alpha * p_mean
                new_p_std = (1 - alpha) * old_base.get("pitch_std", cur_p_std) + alpha * cur_p_std
                new_rate = (1 - alpha) * old_base.get("speech_rate", cur_rate) + alpha * cur_rate

                session["meta"]["acoustic_baseline"] = {
                    "pitch_mean": round(float(new_p_mean), 2),
                    "pitch_std": round(float(new_p_std), 2),
                    "speech_rate": round(float(new_rate), 2),
                }
                session["meta"]["acoustic_turn_count"] = turn + 1

            session["meta"]["pending_acoustic"] = {
                "severity": acoustic_severity,
                "emotion": acoustic_emotion,
                "confidence": acoustic_confidence,
                "anxiety_score": acoustic_features_dict.get("acoustic_anxiety_score", 0.0),
                "pitch_mean": acoustic_features_dict.get("pitch_mean", 0.0),
                "speech_rate": acoustic_features_dict.get("speech_rate", 0.0),
                "pause_ratio": acoustic_features_dict.get("pause_ratio", 0.0),
                "jitter": acoustic_features_dict.get("jitter", 0.0),
                "shimmer": acoustic_features_dict.get("shimmer", 0.0),
                "energy_mean": acoustic_features_dict.get("energy_mean", 0.0),
            }

        return {
            "transcript": transcript,
            "session_id": session_id,
            "acoustic_log_saved": acoustic_log_saved,
            "acoustic": {
                "severity": acoustic_severity,
                "emotion": acoustic_emotion,
                "confidence": acoustic_confidence,
                "anxiety_score": acoustic_features_dict.get("acoustic_anxiety_score", 0.0),
                "pitch_mean": acoustic_features_dict.get("pitch_mean", 0.0),
                "speech_rate": acoustic_features_dict.get("speech_rate", 0.0),
                "pause_ratio": acoustic_features_dict.get("pause_ratio", 0.0),
                "jitter": acoustic_features_dict.get("jitter", 0.0),
                "shimmer": acoustic_features_dict.get("shimmer", 0.0),
            },
        }

    except HTTPException:
        raise
    except Exception:
        print("[voice] Speech-to-text request failed")
        raise HTTPException(status_code=500, detail="Speech-to-text request failed") from None


@router.get("/tts")
def tts(text: str, user: dict = Depends(get_current_user)):
    if not text:
        raise HTTPException(status_code=400, detail="text param is required.")
    try:
        audio_bytes = text_to_speech_bytes(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=response.mp3"},
    )


@router.post("/analyze")
async def analyze_audio(audio: UploadFile = File(...), user: dict = Depends(get_current_user)):
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file.")
    features = extract_features(audio_bytes)
    severity = map_acoustic_to_severity(features.get("acoustic_anxiety_score", 0.0))

    # ── Log to Supabase ──────────────────────────────────────────────────────
    log_to_supabase(session_id="analyze", features=features)
    return {
        "acoustic_severity": severity,
        "acoustic_anxiety_score": features.get("acoustic_anxiety_score"),
        "acoustic_emotion": features.get("acoustic_emotion"),
        "features": features,
    }
