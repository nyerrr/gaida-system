from typing import Dict, Any
from app.utils.logger import log_interaction
from app.services.session_manager import get_session, start_session, record_interaction
from app.services.virtual_agent import detect_intent_and_level, _build_result
from app.services.gpt_agent import generate_response_with_gpt
from app.api.counselor import process_alert


# ---------------------------------------------------------------------------
# Cumulative confidence weights
# 50% history, 50% current message — more responsive than before
# ---------------------------------------------------------------------------
HISTORY_WEIGHT = 0.5
CURRENT_WEIGHT = 0.5

# When the same distress intent repeats across messages, boost current score
# Repetition = escalation signal (student keeps expressing same distress)
REPETITION_BOOST = 1.3

# ---------------------------------------------------------------------------
# Calming keywords — these reduce running confidence
# If student says calming words, anxiety level gradually drops
# ---------------------------------------------------------------------------
CALMING_KEYWORDS = [
    "better", "okay", "ok", "fine", "calm", "good", "thanks", "thank you",
    "relieved", "relaxed", "happy", "magaan na", "okay na", "ayos na",
    "mas okay na", "feel better", "feeling better", "nakakagaan",
    "panatag na", "hindi na", "wala na", "okay na ko", "okay na ako",
]


def _detect_calming(text: str) -> bool:
    """Returns True if the message contains calming/recovery signals."""
    txt = text.lower()
    return any(kw in txt for kw in CALMING_KEYWORDS)


def analyze_intent(user_message: str, session_id: str | None = None) -> Dict[str, Any]:
    """
    Main entry point for processing a student message.

    Flow:
    1. Ensure session exists
    2. Detect intent + raw confidence from current message
    3. Blend with running_confidence from session history (cumulative scoring)
    4. If calming words detected, reduce running confidence
    5. Map blended confidence to anxiety level
    6. Always route to GPT for response
    7. Fire counselor alert if HIGH or CRISIS
    8. Save updated running_confidence back to session

    Returns:
        {
            "session_id": str,
            "intent": str,
            "confidence": float,
            "anxiety_level": str or None,
            "severity": str,
            "anxiety_score": int,
            "response": str,
            "method": str,
        }
    """

    # --- Step 1: Ensure session exists ---
    if session_id and get_session(session_id):
        session = get_session(session_id)
    else:
        session_id = start_session(session_id=session_id)
        session = get_session(session_id)

    # --- Step 2: Detect intent + raw confidence from current message only ---
    detection = detect_intent_and_level(user_message)
    intent = detection["intent"]
    raw_confidence = detection["confidence"]
    crisis_resources = detection["crisis_resources"]

    # --- Step 3: Crisis is always immediate — bypass cumulative scoring ---
    if intent == "suicidal" or raw_confidence >= 0.99:
        running_confidence = 0.99
        session["meta"]["running_confidence"] = running_confidence
        session["meta"]["running_intent"] = intent
    else:
        # Get previous running confidence from session (default 0.3 = neutral start)
        previous_confidence = session.get("meta", {}).get("running_confidence", 0.3)
        previous_intent = session.get("meta", {}).get("running_intent", "neutral")

        # --- Step 4: Check for calming signals ---
        if _detect_calming(user_message):
            # Student seems to be calming down — reduce confidence toward neutral
            running_confidence = (previous_confidence * 0.7) + (0.3 * 0.3)
            running_confidence = max(0.3, round(running_confidence, 3))
        else:
            # Apply repetition boost if same distress intent repeats
            # Repetition signals escalation — student keeps expressing same distress
            boosted_raw = raw_confidence
            if (
                intent == previous_intent
                and intent not in ("neutral", "academic")
                and raw_confidence > 0.3
            ):
                boosted_raw = min(0.98, raw_confidence * REPETITION_BOOST)

            # Cross-intent boost — when two related distress intents appear together
            # e.g. student mentions sadness then anxiety, or anxiety then academic stress
            # Switching between related emotions = escalation signal
            RELATED_INTENTS = {
                "anxiety":    ("stress", "sadness", "academic"),
                "sadness":    ("anxiety", "loneliness", "stress"),
                "stress":     ("anxiety", "academic", "sadness"),
                "academic":   ("anxiety", "stress"),
                "loneliness": ("sadness", "anxiety"),
                "anger":      ("stress", "sadness"),
            }
            related = RELATED_INTENTS.get(intent, ())
            if (
                previous_intent in related
                and raw_confidence > 0.3
                and boosted_raw == raw_confidence  # only if not already boosted above
            ):
                boosted_raw = min(0.98, raw_confidence * 1.15)  # softer 15% cross-intent boost

            # Blend history (50%) with current message (50%)
            running_confidence = (previous_confidence * HISTORY_WEIGHT) + (boosted_raw * CURRENT_WEIGHT)
            running_confidence = round(running_confidence, 3)

        # Keep intent as the most distressed detected so far
        # (intent only upgrades, never downgrades mid-session)
        intent_priority = ["neutral", "academic", "loneliness", "anger", "stress", "sadness", "anxiety", "suicidal"]
        prev_priority = intent_priority.index(previous_intent) if previous_intent in intent_priority else 0
        curr_priority = intent_priority.index(intent) if intent in intent_priority else 0
        intent = intent if curr_priority >= prev_priority else previous_intent

        # Save updated running values back to session
        if "meta" not in session:
            session["meta"] = {}
        session["meta"]["running_confidence"] = running_confidence
        session["meta"]["running_intent"] = intent

    # --- Step 5: Map blended confidence to anxiety level ---
    final_detection = _build_result(intent, running_confidence)
    anxiety_level = final_detection["anxiety_level"]
    severity = final_detection["severity"]
    counselor_protocol = final_detection["counselor_protocol"]
    anxiety_score = final_detection["anxiety_score"]

    # --- Step 6: Build GPT context ---
    gpt_protocol = counselor_protocol
    if crisis_resources:
        gpt_protocol = f"{crisis_resources}\n\n{counselor_protocol or ''}"

    # --- Step 7: Always call GPT ---
    gpt_result = generate_response_with_gpt(
        user_message=user_message,
        session_context=session,
        anxiety_level=anxiety_level,
        counselor_protocol=gpt_protocol,
    )

    if gpt_result.get("used") and gpt_result.get("response"):
        response_text = gpt_result["response"]
        method = "gpt"
    else:
        logger.warning("GPT unavailable, using safe fallback response")
        response_text = "I'm here with you. Can you tell me more about how you're feeling?"
        method = "fallback"

    # --- Step 8: Fire counselor alert for HIGH and CRISIS ---
    if anxiety_level in ("high", "crisis"):
        try:
            process_alert(
                session_id=session_id,
                user_id=session.get("user_id") if session else None,
                intent=intent,
                anxiety_score=anxiety_score,
                message=user_message,
            )
        except Exception as e:
            logger.error(f"Failed to fire counselor alert: {e}")

    # --- Step 9: Record interaction in session ---
    try:
        record_interaction(
            session_id=session_id,
            sender="user",
            text=user_message,
            analysis={
                "intent": intent,
                "confidence": running_confidence,
                "intensity": anxiety_score,
                "escalate": anxiety_level in ("high", "crisis"),
            },
            response=response_text,
        )
    except Exception as e:
        logger.error(f"Failed to record interaction: {e}")

    # Step 9: Return full payload including severity
    return {
        "session_id": session_id,
        "intent": intent,
        "confidence": running_confidence,
        "anxiety_level": anxiety_level,
        "severity": severity,
        "anxiety_score": anxiety_score,
        "response": response_text,
        "method": method,
    }