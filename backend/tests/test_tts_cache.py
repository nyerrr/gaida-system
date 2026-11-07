import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.services.tts as tts


def _reset():
    tts._synthesize_cached.cache_clear()


def test_repeated_text_is_synthesized_once(monkeypatch):
    calls = []

    def fake_synthesize(text, lang):
        calls.append((text, lang))
        return b"fake-mp3"

    monkeypatch.setattr(tts, "_synthesize", fake_synthesize)
    _reset()

    assert tts.text_to_speech_bytes("hello there") == b"fake-mp3"
    assert tts.text_to_speech_bytes("hello there") == b"fake-mp3"

    # The second call must be served from the cache, not from gTTS.
    assert calls == [("hello there", "en")]


def test_different_text_is_synthesized_separately(monkeypatch):
    calls = []

    def fake_synthesize(text, lang):
        calls.append(text)
        return text.encode()

    monkeypatch.setattr(tts, "_synthesize", fake_synthesize)
    _reset()

    assert tts.text_to_speech_bytes("first") == b"first"
    assert tts.text_to_speech_bytes("second") == b"second"
    assert calls == ["first", "second"]


def test_long_text_bypasses_the_cache(monkeypatch):
    calls = []

    def fake_synthesize(text, lang):
        calls.append(text)
        return b"long"

    monkeypatch.setattr(tts, "_synthesize", fake_synthesize)
    _reset()

    long_text = "x" * (tts._MAX_CACHED_CHARS + 1)
    assert tts.text_to_speech_bytes(long_text) == b"long"
    assert tts.text_to_speech_bytes(long_text) == b"long"

    # Over the cap: synthesized every time so one huge reply can't occupy the
    # cache, and the cache stays empty.
    assert calls == [long_text, long_text]
    assert tts._synthesize_cached.cache_info().currsize == 0
