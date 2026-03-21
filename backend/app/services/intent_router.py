from typing import Dict, Any
import logging
from app.services.session_manager import get_session, start_session, record_interaction
from app.services.virtual_agent import detect_intent_and_level, _build_result
from app.services.gpt_agent import generate_response_with_gpt
from app.api.counselor import process_alert

logger = logging.getLogger(__name__)

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

# ---------------------------------------------------------------------------
# Urgent physical symptom keywords
# These are immediate, observable anxiety symptoms
# When detected, current message gets 70% weight instead of 50%
# so confidence jumps faster regardless of history
# ---------------------------------------------------------------------------
URGENT_PHYSICAL_KEYWORDS = [
    "cant breathe", "can't breathe", "cannot breathe",
    "chest is tight", "tight chest", "chest tightness", "chest pain",
    "shaking", "trembling", "nanginginig",
    "hyperventilating", "hyperventilation",
    "panic attack", "panicattack",
    "cant control my breathing", "cant control breathing",
    "dizzy", "lightheaded",
    "palpitations", "heart racing",
    "sikip sa puso", "hirap huminga",
    "di makahininga",
]


def _detect_calming(text: str) -> bool:
    """Returns True if the message contains calming/recovery signals."""
    txt = text.lower()
    return any(kw in txt for kw in CALMING_KEYWORDS)


def _detect_urgent(text: str) -> bool:
    """Returns True if the message contains urgent physical anxiety symptoms."""
    txt = text.lower()
    return any(kw in txt for kw in URGENT_PHYSICAL_KEYWORDS)


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
        session_id = start_session()
        session = get_session(session_id)

    # --- Step 2: Detect intent + raw confidence from current message only ---
    detection = detect_intent_and_level(user_message)
    intent = detection["intent"]
    raw_confidence = detection["confidence"]
    crisis_resources = detection["crisis_resources"]

    # --- Step 3: Crisis is always immediate — bypass cumulative scoring ---
    if intent == "suicidal" or raw_confidence >= 0.99:
        running_confidence = 0.99
        if "meta" not in session:
            session["meta"] = {}
        session["meta"]["running_confidence"] = running_confidence
        session["meta"]["running_intent"] = "suicidal"
        session["meta"]["post_crisis"] = True  # ← flag stays for entire session
    else:
        # Get previous running confidence from session (default 0.3 = neutral start)
        previous_confidence = session.get("meta", {}).get("running_confidence", 0.3)
        previous_intent = session.get("meta", {}).get("running_intent", "neutral")
        post_crisis = session.get("meta", {}).get("post_crisis", False)

        # --- Step 4: Check for calming signals ---
        if _detect_calming(user_message):
            if post_crisis:
                # After crisis — drop faster (50/50) but floor at 0.3
                running_confidence = (previous_confidence * 0.5) + (0.3 * 0.5)
            else:
                # Normal calming — also faster now (50/50 instead of 70/30)
                running_confidence = (previous_confidence * 0.5) + (0.3 * 0.5)
            running_confidence = max(0.3, round(running_confidence, 3))
        else:
            # Apply repetition boost if same distress intent repeats
            boosted_raw = raw_confidence
            if (
                intent == previous_intent
                and intent not in ("neutral", "academic")
                and raw_confidence > 0.3
            ):
                boosted_raw = min(0.98, raw_confidence * REPETITION_BOOST)

            # Cross-intent boost
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
                and boosted_raw == raw_confidence
            ):
                boosted_raw = min(0.98, raw_confidence * 1.15)

            # Blend history vs current message
            # Urgent physical symptoms get 70% weight — jump faster
            # Normal messages get 50% weight — build gradually
            if _detect_urgent(user_message):
                running_confidence = (previous_confidence * 0.3) + (boosted_raw * 0.7)
            else:
                running_confidence = (previous_confidence * HISTORY_WEIGHT) + (boosted_raw * CURRENT_WEIGHT)
            running_confidence = round(running_confidence, 3)

        # Intent priority — after crisis, allow downgrade when calming detected
        # Before this fix: intent was locked to "suicidal" forever
        # Now: if student is clearly calming, allow intent to reflect current state
        intent_priority = ["neutral", "academic", "loneliness", "anger", "stress", "sadness", "anxiety", "suicidal"]
        prev_priority = intent_priority.index(previous_intent) if previous_intent in intent_priority else 0
        curr_priority = intent_priority.index(intent) if intent in intent_priority else 0

        if post_crisis and _detect_calming(user_message):
            # Allow downgrade after crisis when student is calming
            # Intent follows current detection, not locked to suicidal
            pass  # intent stays as currently detected
        else:
            # Normal behavior — intent only upgrades
            intent = intent if curr_priority >= prev_priority else previous_intent

        # Save updated running values back to session
        if "meta" not in session:
            session["meta"] = {}
        session["meta"]["running_confidence"] = running_confidence
        session["meta"]["running_intent"] = intent
        session["meta"]["post_crisis"] = post_crisis  # preserve flag

    # --- Step 5: Map blended confidence to anxiety level ---
    post_crisis = session.get("meta", {}).get("post_crisis", False)
    final_detection = _build_result(intent, running_confidence, post_crisis=post_crisis)
    anxiety_level = final_detection["anxiety_level"]
    severity = final_detection["severity"]
    counselor_protocol = final_detection["counselor_protocol"]
    anxiety_score = final_detection["anxiety_score"]

    # --- Step 5b: Fuse with acoustic features if available ---
    # When user spoke before typing, acoustic features are saved in session
    # We take the higher of text severity vs acoustic severity
    pending_acoustic = session.get("meta", {}).get("pending_acoustic")
    if pending_acoustic:
        try:
            from app.analytics.acoustic_features import fuse_with_text_severity
            acoustic_severity = pending_acoustic.get("severity", "Normal")
            acoustic_emotion = pending_acoustic.get("emotion", "neutral")
            acoustic_confidence = pending_acoustic.get("confidence", 0.0)

            fused_severity = fuse_with_text_severity(
                acoustic_severity=acoustic_severity,
                text_severity=severity,
                acoustic_emotion=acoustic_emotion,
            )

            # If acoustic bumped severity up — update anxiety level too
            severity_order = {"Normal": 0, "Low": 1, "Moderate": 2, "High": 3}
            if severity_order.get(fused_severity, 0) > severity_order.get(severity, 0):
                severity = fused_severity
                # Remap anxiety_level and anxiety_score from new severity
                severity_to_level = {
                    "Low": ("low", 1),
                    "Moderate": ("moderate", 3),
                    "High": ("high", 5),
                }
                if fused_severity in severity_to_level:
                    anxiety_level, anxiety_score = severity_to_level[fused_severity]
                    counselor_protocol = final_detection.get("counselor_protocol")

            # Clear pending acoustic after use
            session["meta"]["pending_acoustic"] = None

            logger.info(f"Acoustic fusion: text={final_detection['severity']} acoustic={acoustic_severity} fused={severity}")
        except Exception as e:
            logger.error(f"Acoustic fusion error: {e}")

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