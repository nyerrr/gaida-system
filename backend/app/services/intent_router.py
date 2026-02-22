import re
import uuid

from app.services.rule_intent import analyze_with_rules
from app.services.intent_model import predict_intent
from app.services.gpt_agent import generate_response_with_gpt
from app.services.virtual_agent import generate_response
from app.utils.logger import log_interaction
from app.analytics.anxiety_scoring import score_anxiety
from app.services.session_manager import record_interaction, get_session
from app.api.counselor import process_alert


# ---------------------------------------------------------------------------
# Informational / FAQ guard
# ---------------------------------------------------------------------------

_QUESTION_PATTERN = re.compile(
    r"\b(para saan|para sa ano|what is|ano ang|ano ito|ano ba|paano|"
    r"how (do|does|can|is)|what (can|does|is|are)|sino|bakit|anong|"
    r"pwede ba|gamitin|gamit|explain|tell me about|what does|"
    r"saan|app|application|itong app|yung app|purpose|function|"
    r"features|feature|about this|tungkol)\b",
    re.IGNORECASE,
)

_MAX_INFORMATIONAL_WORDS = 20


def _is_informational(text: str) -> bool:
    stripped = text.strip()
    word_count = len(stripped.split())
    if word_count <= 2:
        return True
    return bool(_QUESTION_PATTERN.search(stripped)) and word_count <= _MAX_INFORMATIONAL_WORDS


# ---------------------------------------------------------------------------
# Main intent analysis
# ---------------------------------------------------------------------------

def analyze_intent(user_message: str, session_id: str | None = None, user_id: str | None = None):

    # Step 0: Generate a session ID if none is provided
    if session_id is None:
        session_id = str(uuid.uuid4())

    # Step 1: Rule-based intent detection first
    rule_result = analyze_with_rules(user_message)
    rule_intent = rule_result.get("intent") if rule_result else None

    if rule_result and rule_intent not in ("neutral", None):
        intent = rule_intent
        confidence = rule_result["confidence"]
        method = "rule-based"

    elif _is_informational(user_message):
        intent = "faq"
        confidence = 0.95
        method = "rule-based (informational guard)"

    else:
        # Step 2: Fall back to ML model
        model_result = predict_intent(user_message)
        intent = model_result["intent"]
        confidence = model_result["confidence"]
        method = "ml-model"

    # Step 3: Compute anxiety score and map to severity level
    anxiety_score = score_anxiety(intent)

    # Step 4: Process severity and trigger counselor alert if High
    counselor_result = process_alert(
        session_id=session_id,
        user_id=user_id,
        intent=intent,
        anxiety_score=anxiety_score,
        message=user_message,
    )
    severity = counselor_result["severity"]
    alert_sent = counselor_result["alert_sent"]

    # Step 5: Generate static fallback response from virtual_agent
    response_text = generate_response({
        "intent": intent,
        "confidence": confidence
    })

    # Step 6: Enhance response with GPT only for emotional intents
    try:
        session_ctx = get_session(session_id)
    except Exception:
        session_ctx = None

    if intent not in ("neutral", "faq", "other", "unknown"):
        gpt_result = generate_response_with_gpt(user_message, session_ctx)
        if gpt_result.get("used") and gpt_result.get("response"):
            response_text = gpt_result["response"]

    # Step 7: Log interaction
    log_interaction(
        session_id=session_id,
        user_message=user_message,
        intent=intent,
        confidence=confidence,
        anxiety_score=anxiety_score,
        response=response_text,
        method=method
    )

    # Step 8: Record into session store for counselor live view
    record_interaction(
        session_id=session_id,
        sender="user",
        text=user_message,
        analysis=rule_result if rule_result else {"intent": intent, "confidence": confidence},
        response=None
    )

    record_interaction(
        session_id=session_id,
        sender="bot",
        text=response_text,
        analysis={
            "intent": intent,
            "confidence": confidence,
            "anxiety_score": anxiety_score,
            "severity": severity,
            "alert_sent": alert_sent,
        },
        response=response_text
    )

    # Step 9: Return full payload including severity
    return {
        "session_id": session_id,
        "intent": intent,
        "confidence": confidence,
        "anxiety_score": anxiety_score,
        "severity": severity,
        "alert_sent": alert_sent,
        "response": response_text,
        "method": method
    }