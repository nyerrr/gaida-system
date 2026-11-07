from functools import lru_cache
from io import BytesIO

from gtts import gTTS

# Long replies are synthesized on every request instead of being pinned in
# memory; the cache is there to absorb repeat listens on the same message, not
# to store an unbounded corpus of whole transcripts.
_MAX_CACHED_CHARS = 2000

# gTTS normally answers in well under a second, but it talks to an external
# service with no SLA. Without a timeout a stalled socket can pin a worker
# thread indefinitely, so fail fast and let the endpoint return a 500.
_TIMEOUT_SECONDS = 15


def _synthesize(text: str, lang: str) -> bytes:
    tts = gTTS(text=text, lang=lang, timeout=_TIMEOUT_SECONDS)
    buf = BytesIO()
    tts.write_to_fp(buf)
    return buf.getvalue()


# Repeat clicks on the same reply (and the same reply replayed by another
# student) reuse the encoded MP3 instead of re-calling Google. ~60 KB per
# entry, so 64 entries ≈ 4 MB worst case.
@lru_cache(maxsize=64)
def _synthesize_cached(text: str, lang: str) -> bytes:
    return _synthesize(text, lang)


def text_to_speech_bytes(text: str, lang: str = "en") -> bytes:
    if len(text) <= _MAX_CACHED_CHARS:
        return _synthesize_cached(text, lang)
    return _synthesize(text, lang)
