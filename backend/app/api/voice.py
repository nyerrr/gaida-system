import whisper
import tempfile
import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from app.services.tts import text_to_speech_bytes

router = APIRouter(prefix="/audio", tags=["audio"])

# Load Whisper model once at startup (use "base" for speed, "small"/"medium" for accuracy)
model = whisper.load_model("base")


@router.post("/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    """
    Accepts an audio file (webm, wav, mp3, etc.) from the browser.
    Returns the transcript as plain text.
    """
    if not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio type.")

    # Save upload to a temp file so Whisper can read it
    suffix = os.path.splitext(audio.filename or "audio.webm")[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    try:
        result = model.transcribe(tmp_path)
        transcript = result.get("text", "").strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        os.unlink(tmp_path)

    return {"transcript": transcript}


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
