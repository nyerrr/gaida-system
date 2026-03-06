import re
import uuid

from app.services.rule_intent import analyze_with_rules
from app.services.intent_model import predict_intent  # now uses fine-tuned GPT
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

    # very short questions must still contain a keyword
    if word_count <= 2:
        return bool(_QUESTION_PATTERN.search(stripped))

    return bool(_QUESTION_PATTERN.search(stripped)) and word_count <= _MAX_INFORMATIONAL_WORDS


# ---------------------------------------------------------------------------
# Main intent analysis (confidence-based selection)
# ---------------------------------------------------------------------------

def analyze_intent(user_message: str, session_id: str | None = None, user_id: str | None = None):

    if session_id is None:
        session_id = str(uuid.uuid4())

    # --- Rule-based prediction ---
    rule_result = analyze_with_rules(user_message)
    if rule_result:
        rule_intent = rule_result.get("intent") or "other"
        rule_confidence = float(rule_result.get("confidence", 0.5))
    else:
        rule_intent = "other"
        rule_confidence = 0.0

    # --- Informational FAQ guard overrides ---
    if _is_informational(user_message):
        rule_intent = "faq"
        rule_confidence = 0.95

    # --- GPT / ML prediction ---
    model_result = predict_intent(user_message)
    model_intent = model_result["intent"]
    model_confidence = model_result["confidence"]

    # --- Choose the higher confidence result ---
    if rule_confidence >= model_confidence:
        intent = rule_intent
        confidence = rule_confidence
        method = "rule-based"
    else:
        intent = model_intent
        confidence = model_confidence
        method = "ml-model"

    # --- Anxiety scoring ---
    anxiety_score = score_anxiety(intent)

    # --- Counselor alert ---
    counselor_result = process_alert(
        session_id=session_id,
        user_id=user_id,
        intent=intent,
        anxiety_score=anxiety_score,
        message=user_message,
    )
    severity = counselor_result["severity"]
    alert_sent = counselor_result["alert_sent"]

    # --- Generate fallback response ---
    response_text = generate_response({
        "intent": intent,
        "confidence": confidence
    })

    # --- Enhance with GPT if emotional intent ---
    try:
        session_ctx = get_session(session_id)
    except Exception:
        session_ctx = None

    if intent not in ("neutral", "faq", "other", "unknown"):
        gpt_result = generate_response_with_gpt(user_message, session_ctx)
        if gpt_result.get("used") and gpt_result.get("response"):
            response_text = gpt_result["response"]

    # --- Logging ---
    log_interaction(
        session_id=session_id,
        user_message=user_message,
        intent=intent,
        confidence=confidence,
        anxiety_score=anxiety_score,
        response=response_text,
        method=method
    )

    # --- Record interactions ---
    record_interaction(
        session_id=session_id,
        sender="user",
        text=user_message,
        analysis={
            "rule": rule_result or {},
            "model": model_result,
            "chosen": {"intent": intent, "confidence": confidence}
        },
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