import whisper
import tempfile
import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from app.services.tts import text_to_speech_bytes
from app.analytics.acoustic_features import extract_features, map_acoustic_to_severity

router = APIRouter(prefix="/audio", tags=["audio"])

# Load Whisper model once at startup
model = whisper.load_model("base")


@router.post("/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    """
    Accepts an audio file (webm, wav, mp3, etc.) from the browser.
    Returns transcript + acoustic features + acoustic severity.
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
    except Exception:
        acoustic_features = {}
        acoustic_severity = "Low"

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

    return {
        "transcript": transcript,
        "acoustic": acoustic_features,
        "acoustic_severity": acoustic_severity,
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
        "features": features,
    }