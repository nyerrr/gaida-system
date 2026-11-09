from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import voice
from app.main import app
from app.utils.auth import get_current_user


@pytest.fixture
def voice_client(monkeypatch):
    session_id = "voice-persistence-session"
    session = {"session_id": session_id, "user_id": "student-1", "meta": {}}
    monkeypatch.setattr(voice, "get_session", lambda _session_id: session)
    monkeypatch.setattr(
        voice,
        "extract_features",
        lambda _audio, baseline=None: {
            "duration": 1.5,
            "acoustic_anxiety_score": 0.2,
            "acoustic_emotion": "neutral",
            "acoustic_confidence": 0.6,
        },
    )
    monkeypatch.setattr(
        voice,
        "_get_voice_client",
        lambda: SimpleNamespace(
            audio=SimpleNamespace(
                transcriptions=SimpleNamespace(
                    create=lambda **_kwargs: SimpleNamespace(text="I feel okay today")
                )
            )
        ),
    )
    app.dependency_overrides[get_current_user] = lambda: {"user_id": "student-1"}
    with TestClient(app) as client:
        yield client, session_id
    app.dependency_overrides.pop(get_current_user, None)


def _post_voice(client, session_id):
    return client.post(
        "/audio/speech-to-text",
        data={"session_id": session_id},
        files={"audio": ("recording.wav", b"fake audio", "audio/wav")},
    )


def test_voice_route_reports_successful_acoustic_log(voice_client, monkeypatch):
    client, session_id = voice_client
    logged = {}

    def save_log(*, session_id, features):
        logged.update(session_id=session_id, features=features)
        return True

    monkeypatch.setattr(voice, "log_to_supabase", save_log)

    response = _post_voice(client, session_id)

    assert response.status_code == 200
    assert response.json()["transcript"] == "I feel okay today"
    assert response.json()["acoustic_log_saved"] is True
    assert logged["session_id"] == session_id
    assert logged["features"]["duration"] == 1.5


def test_voice_route_reports_failed_acoustic_log(voice_client, monkeypatch):
    client, session_id = voice_client
    monkeypatch.setattr(voice, "log_to_supabase", lambda **_kwargs: False)

    response = _post_voice(client, session_id)

    assert response.status_code == 200
    assert response.json()["acoustic_log_saved"] is False


def test_voice_route_logs_features_even_when_transcription_fails(voice_client, monkeypatch):
    client, session_id = voice_client
    logged = []

    def fail_transcription(**_kwargs):
        raise RuntimeError("transcription provider unavailable")

    monkeypatch.setattr(
        voice,
        "_get_voice_client",
        lambda: SimpleNamespace(
            audio=SimpleNamespace(
                transcriptions=SimpleNamespace(create=fail_transcription)
            )
        ),
    )
    monkeypatch.setattr(
        voice,
        "log_to_supabase",
        lambda **kwargs: logged.append(kwargs) or True,
    )

    response = _post_voice(client, session_id)

    assert response.status_code == 500
    assert len(logged) == 1
    assert logged[0]["session_id"] == session_id
