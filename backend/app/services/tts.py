from gtts import gTTS
from io import BytesIO

def text_to_speech_bytes(text: str, lang: str = "en") -> bytes:
    tts = gTTS(text=text, lang=lang)
    buf = BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()