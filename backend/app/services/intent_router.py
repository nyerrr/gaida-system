from app.services.rule_intent import analyze_with_rules
from app.services.gpt_intent import analyze_with_gpt
from app.services.virtual_agent import generate_response
from app.services.gpt_agent import generate_response_with_gpt
from app.utils.logger import log_interaction
from app.analytics.anxiety_scoring import score_anxiety
import uuid
from app.services.session_manager import record_interaction, start_session


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
    # First attempt rule-based/static responses
    response_text = generate_response({
        "intent": intent,
        "confidence": confidence
    })

    # Then try GPT-based response using session context (prefer GPT if available)
    try:
        from app.services.session_manager import get_session
        session_ctx = get_session(session_id)
    except Exception:
        session_ctx = None

    gpt_result = generate_response_with_gpt(user_message, session_ctx)
    if gpt_result.get("used") and gpt_result.get("response"):
        response_text = gpt_result["response"]

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

    # Record into in-memory session store for live viewing by counselors/coordinator
    # user message entry
    record_interaction(
        session_id=session_id,
        sender="user",
        text=user_message,
        analysis=rule_result if rule_result else {"intent": intent, "confidence": confidence},
        response=None
    )

    # bot response entry
    record_interaction(
        session_id=session_id,
        sender="bot",
        text=response_text,
        analysis={"intent": intent, "confidence": confidence, "anxiety_score": anxiety_score},
        response=response_text
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
