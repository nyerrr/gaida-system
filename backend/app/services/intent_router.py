from app.services.rule_intent import analyze_with_rules
from app.services.gpt_intent import analyze_with_gpt
from app.services.virtual_agent import generate_response
from app.utils.logger import log_interaction
import uuid

def analyze_intent(user_message: str, session_id: str | None = None):

    #Generate a session ID for logging purposes
    if session_id is None:
        session_id = str(uuid.uuid4())

    # Step 1: Rule-based first
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
    # Step 2: Generate the agent response so we can log and check it
    response_text = generate_response({"intent": intent, "confidence": confidence})

    # Step 3: Log interaction with actual response for appropriateness/safety checks
    log_interaction(
        session_id=session_id,
        user_message=user_message,
        intent=intent,
        confidence=confidence,
        response=response_text,
        method=method
    )

    # Step 4: Return intent, confidence and the generated response
    return {
        "session_id": session_id,
        "intent": intent,
        "confidence": confidence,
        "response": response_text,
        "method": method
    }
