from fastapi.testclient import TestClient

from app.services.rule_intent import analyze_with_rules
from app.services.virtual_agent import generate_response
import app.services.intent_router as intent_router
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
