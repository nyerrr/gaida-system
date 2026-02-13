from app.services.rule_intent import analyze_with_rules
from app.services.gpt_intent import analyze_with_gpt
from app.services.virtual_agent import generate_response
from app.utils.logger import log_interaction
from app.analytics.anxiety_scoring import score_anxiety
import uuid


def analyze_intent(user_message: str, session_id: str | None = None):

    # Step 0: Generate a session ID if none is provided
    if session_id is None:
        session_id = str(uuid.uuid4())

    # Step 1: Rule-based intent detection first
    rule_result = analyze_with_rules(user_message)

    if rule_result:
        intent = rule_result["intent"]
        confidence = rule_result["confidence"]
        method = "rule-based"
    else:
        gpt_result = analyze_with_gpt(user_message)
        intent = gpt_result["intent"]
        confidence = gpt_result["confidence"]
        method = "gpt"

    # Step 2: Compute anxiety-level score (analytics)
    anxiety_score = score_anxiety(intent)

    # Step 3: Generate the agent response
    response_text = generate_response({
        "intent": intent,
        "confidence": confidence
    })

    # Step 4: Log interaction (only logged if consent exists)
    log_interaction(
        session_id=session_id,
        user_message=user_message,
        intent=intent,
        confidence=confidence,
        anxiety_score=anxiety_score,
        response=response_text,
        method=method
    )

    # Step 5: Return full response payload
    return {
        "session_id": session_id,
        "intent": intent,
        "confidence": confidence,
        "anxiety_score": anxiety_score,
        "response": response_text,
        "method": method
    }
