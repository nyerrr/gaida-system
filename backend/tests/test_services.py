from fastapi.testclient import TestClient

from app.services.rule_intent import analyze_with_rules
from app.services.virtual_agent import generate_response
import app.services.intent_router as intent_router
import json
from app.main import app


def test_rule_intent_basic():
    res = analyze_with_rules("I feel very anxious and nervous today")
    assert isinstance(res, dict)
    assert "intent" in res and "confidence" in res
    assert res["intent"] in ("anxiety", "neutral", "sadness", "stress", "other")
    assert 0.0 <= res["confidence"] <= 1.0


def test_generate_response_matches_intent():
    assert "anxious" in generate_response({"intent": "anxiety"}).lower()


def test_virtual_agent_endpoint():
    # Force rule-based analysis for tests
    intent_router.USE_GPT = False
    client = TestClient(app)
    r = client.post("/virtual-agent", json={"message": "I'm nervous and anxious"})
    assert r.status_code == 200
    data = r.json()
    assert "intent" in data and "confidence" in data and "response" in data


def test_logging_format(tmp_path, monkeypatch):
    # redirect log file to a temporary location so we don't pollute workspace
    from app.utils import logger

    log_path = tmp_path / "interactions.json"
    monkeypatch.setattr(logger, "LOG_FILE", log_path)

    # clear any existing content
    if log_path.exists():
        log_path.unlink()

    # make sure the fake session is allowed to write
    monkeypatch.setattr("app.utils.logger.has_consent", lambda *_: True)
    monkeypatch.setattr("app.services.session_manager.has_consent", lambda *_: True)

    # perform an analysis which should write a new log
    result = intent_router.analyze_intent("hello there")
    assert "session_id" in result

    # read back file and verify format
    with open(log_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, list) and len(data) >= 1
    # check each log item adheres to schema
    session_ids = {entry.get("session_id") for entry in data}
    # they should all use the same id now that record_interaction preserves it
    assert len(session_ids) == 1, f"unexpected multiple session IDs: {session_ids}"

    for entry in data:
        for key in [
            "timestamp",
            "session_id",
            "user_message",
            "intent",
            "confidence",
            "anxiety_score",
            "response",
            "method",
        ]:
            assert key in entry
