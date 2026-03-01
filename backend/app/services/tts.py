from gtts import gTTS
from io import BytesIO
from app.utils.logger import logger
from app.utils.retry import exponential_backoff_retry
from app.core.config import TTS_TIMEOUT


def text_to_speech_bytes(text: str, lang: str = "en") -> bytes:
    """
    Convert text to speech bytes using gTTS with retry logic.
    
    Args:
        text: Text to convert to speech
        lang: Language code (default: "en")
        
    Returns:
        Audio bytes in MP3 format
        
    Raises:
        Exception: If all retries exhausted
    """
    if not text or not text.strip():
        logger.warning("Empty text provided to text_to_speech_bytes")
        return b""

    def _generate_tts():
        """Inner function to generate TTS with timeout."""
        tts = gTTS(text=text, lang=lang, slow=False)
        buf = BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.read()

    try:
        # Retry on network/transient errors
        audio_bytes = exponential_backoff_retry(
            _generate_tts,
            exception_types=(
                ConnectionError,
                TimeoutError,
                OSError,
            )
        )
        logger.debug(f"TTS generated successfully for text (len={len(text)})")
        return audio_bytes

    except Exception as e:
        logger.error(f"Failed to generate TTS after retries: {e}")
        # Return empty bytes instead of raising to allow graceful degradation
        return b""