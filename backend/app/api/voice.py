import whisper
import tempfile
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import Response
from app.services.tts import text_to_speech_bytes
from app.analytics.acoustic_features import (
    extract_features,
    map_acoustic_to_severity,
    fuse_with_text_severity,
)
from app.services.intent_router import analyze_intent

router = APIRouter(prefix="/audio", tags=["audio"])

# Load Whisper model once at startup
model = whisper.load_model("base")


@router.post("/speech-to-text")
async def speech_to_text(
    audio: UploadFile = File(...),
    session_id: str = Form(None),
):
    """
    Accepts an audio file (webm, wav, mp3, etc.) from the browser.
    Returns transcript + acoustic features + full intent analysis + AI response.
    """
    if not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio type.")

    suffix = os.path.splitext(audio.filename or "audio.webm")[1] or ".webm"
    audio_bytes = await audio.read()

    # Step 1: Acoustic feature extraction
    try:
        acoustic_features = extract_features(audio_bytes)
        acoustic_severity = map_acoustic_to_severity(
            acoustic_features.get("acoustic_anxiety_score", 0.0)
        )
        acoustic_confidence = acoustic_features.get("acoustic_confidence", 1.0)
        acoustic_emotion = acoustic_features.get("acoustic_emotion", "neutral")
    except Exception as e:
        print(f"Acoustic extraction error: {e}")
        acoustic_features = {}
        acoustic_severity = "Normal"
        acoustic_confidence = 0.0
        acoustic_emotion = "neutral"

    # Step 2: Whisper transcription
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        result = model.transcribe(tmp_path)
        transcript = result.get("text", "").strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        os.unlink(tmp_path)

    # Step 3: Run intent analysis on transcript (same as chat)
    intent_result = {}
    if transcript:
        try:
            intent_result = analyze_intent(
                user_message=transcript,
                session_id=session_id,
            )
        except Exception as e:
            print(f"Intent analysis error: {e}")

    # Step 4: Fuse acoustic severity with text severity
    text_severity = intent_result.get("severity", "Normal")
    fused_severity = fuse_with_text_severity(
        acoustic_severity=acoustic_severity,
        text_severity=text_severity,
        acoustic_confidence=acoustic_confidence,
    )

    # Step 5: Override anxiety level if acoustic is higher
    # e.g. student sounds anxious even if words seem neutral
    severity_order = {"Normal": 0, "Low": 1, "Moderate": 2, "High": 3}
    if severity_order.get(acoustic_severity, 0) > severity_order.get(text_severity, 0):
        print(f"Acoustic override: {acoustic_severity} > {text_severity} (emotion: {acoustic_emotion})")

    return {
        "transcript": transcript,
        "session_id": intent_result.get("session_id"),
        "intent": intent_result.get("intent"),
        "confidence": intent_result.get("confidence"),
        "anxiety_level": intent_result.get("anxiety_level"),
        "severity": fused_severity,
        "anxiety_score": intent_result.get("anxiety_score"),
        "response": intent_result.get("response"),
        "method": intent_result.get("method"),
        "acoustic": {
            "severity": acoustic_severity,
            "emotion": acoustic_emotion,
            "confidence": acoustic_confidence,
            "anxiety_score": acoustic_features.get("acoustic_anxiety_score", 0.0),
            "pitch_mean": acoustic_features.get("pitch_mean", 0.0),
            "speech_rate": acoustic_features.get("speech_rate", 0.0),
            "pause_ratio": acoustic_features.get("pause_ratio", 0.0),
            "jitter": acoustic_features.get("jitter", 0.0),
            "shimmer": acoustic_features.get("shimmer", 0.0),
        },
    }


@router.get("/tts")
def tts(text: str):
    """
    Accepts a text query param and returns mp3 audio bytes.
    Example: GET /audio/tts?text=Hello
    """
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
async def analyze_audio(audio: UploadFile = File(...)):
    """
    Runs acoustic feature extraction only, no transcription.
    Use this to test the acoustic pipeline separately.
    """
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file.")

    features = extract_features(audio_bytes)
    severity = map_acoustic_to_severity(features.get("acoustic_anxiety_score", 0.0))

    return {
        "acoustic_severity": severity,
        "acoustic_anxiety_score": features.get("acoustic_anxiety_score"),
        "acoustic_emotion": features.get("acoustic_emotion"),
        "acoustic_confidence": features.get("acoustic_confidence"),
        "features": features,
    }