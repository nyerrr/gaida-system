import re
import random
from typing import Tuple
from difflib import SequenceMatcher

PHRASE_FUZZY_THRESHOLD = 0.70
TOKEN_FUZZY_THRESHOLD = 0.82
FUZZY_WEIGHT_MULTIPLIER = 0.9

# ---------------------------------------------------------------------------
# COUNSELOR FIRST AID PROTOCOLS
# ---------------------------------------------------------------------------

COUNSELOR_PROTOCOLS = {
    "low": """
        # LOW ANXIETY FIRST AID PROTOCOL
        # TO BE FILLED IN AFTER COUNSELOR INTERVIEW
        # Example structure:
        # - Acknowledge the feeling without alarming the student
        # - Suggest a simple grounding exercise (e.g. 4-7-8 breathing)
        # - Remind them this is normal and manageable
        # - Encourage them to keep talking
    """,

    "moderate": """
        # MODERATE ANXIETY FIRST AID PROTOCOL
        # TO BE FILLED IN AFTER COUNSELOR INTERVIEW
        # Example structure:
        # - Validate that what they are feeling is real and serious
        # - Guide them through a specific coping technique
        # - Ask them to describe their physical symptoms
        # - Let them know the counselor is aware
    """,

    "high": """
        # HIGH ANXIETY FIRST AID PROTOCOL
        # TO BE FILLED IN AFTER COUNSELOR INTERVIEW
        # Example structure:
        # - Respond with calm urgency
        # - Immediately inform that counselor has been notified
        # - Guide them through an emergency grounding technique
        # - Keep them talking and present
        # - Do not leave them alone in the conversation
    """,

    "crisis": """
        # CRISIS / SUICIDAL PROTOCOL
        # TO BE FILLED IN AFTER COUNSELOR INTERVIEW
        # Example structure:
        # - Express immediate care and concern
        # - Provide crisis hotline: (insert number)
        # - Provide school guidance office contact
        # - Stay present in the conversation
        # - Never minimize or dismiss what they are feeling
    """,
}

# ---------------------------------------------------------------------------
# CRISIS SAFETY RESOURCES
# ---------------------------------------------------------------------------

CRISIS_RESOURCES = """
Please reach out for immediate help:
- National Crisis Hotline: 1553 (available 24/7)
- In Touch Crisis Line: (02) 893-7603
- School Guidance Office: please visit or call them now
- If in immediate danger, call 911
"""

# ---------------------------------------------------------------------------
# KEYWORDS — used for suicidal check only
# (ML handles general intent, rule_intent.py handles fallback)
# ---------------------------------------------------------------------------

KEYWORDS = {
    "suicidal": [
        ("gusto ko na mamatay", 3.5),
        ("ayoko na mabuhay", 3.5),
        ("magpapakamatay", 3.5),
        ("papatayin ko sarili ko", 3.5),
        ("i want to die", 3.5),
        ("kill myself", 3.5),
        ("end my life", 3.5),
        ("take my own life", 3.5),
        ("suicide", 3.5),
        ("suicidal", 3.5),
        ("tapusin ko na ang buhay ko", 3.5),
        ("tapusin ko na ang lahat", 3.0),
        ("sana wala na lang ako", 3.5),
        ("sana hindi na ako nagising", 3.5),
        ("pagod na ako mabuhay", 3.5),
        ("ayoko nang mabuhay", 3.5),
        ("wala na akong dahilan para mabuhay", 3.5),
        ("wala na akong dahilan", 3.0),
        ("gusto ko nang mawala sa mundo", 3.5),
        ("gusto ko nang mawala sa lahat", 3.5),
    ],
}


def _normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    txt = text.lower()
    txt = re.sub(r"[\u2018\u2019\u201c\u201d]", "'", txt)
    txt = re.sub(r"[^\w\s']+", ' ', txt)
    txt = re.sub(r'(.)\1{2,}', r'\1', txt)
    txt = re.sub(r"\s+", ' ', txt).strip()
    return txt


def _tokenize(text: str):
    return re.findall(r"\w+'?\w*|\w+", text)


# ---------------------------------------------------------------------------
# NEGATIVE CONTEXT PATTERNS
# Applied to ML confidence to reduce false positives
# ---------------------------------------------------------------------------

NEGATIVE_CONTEXTS = [
    (re.compile(r"\b(used to|before|last time|yesterday|last week|last month|dati|noon|noong)\b"), 0.3),
    (re.compile(r"\b(but (im|i'm|i am) (better|okay|fine|good)|better now|okay na|ayos na)\b"), 0.2),
    (re.compile(r"\b(not|no longer|never|wala|hindi|hindi na|di na|wala na)\b"), 0.4),
    (re.compile(r"\b(dying of (laughter|boredom|cuteness)|dead (tired|serious)|i('m| am) dead|lol|haha|hehe|joke|kidding|char)\b"), 0.1),
    (re.compile(r"\b(killed it|crushing it|nailed it|aced it|passed|pumasa|pumasa ako)\b"), 0.1),
    (re.compile(r"\b(my (friend|classmate|roommate|sister|brother|mom|dad|kaibigan|kaklase))\b"), 0.3),
    (re.compile(r"^(do you|are you|can you|have you|did you|would you)\b"), 0.2),
    (re.compile(r"\b(if (i|you) (were|was|feel|felt)|hypothetically|parang kung)\b"), 0.3),
    (re.compile(r"\b(movie|film|show|series|character|scene|story|novel|book|anime|episode|fiction|sa pelikula|sa kwento)\b"), 0.1),
]


def _get_negative_context_multiplier(txt: str) -> float:
    multiplier = 1.0
    for pattern, reduction in NEGATIVE_CONTEXTS:
        if pattern.search(txt):
            multiplier = min(multiplier, reduction)
    return multiplier


def detect_intent_and_level(text: str) -> dict:
    """
    Detects intent and maps it to an anxiety level.

    Flow:
    1. Suicidal keyword check (rule-based — always runs first)
    2. ML classifier (primary detection)
    3. rule_intent.py (fallback if ML fails — better than old keyword scoring)
    """
    txt = _normalize_text(text)
    tokens = set(_tokenize(txt))

    # -------------------------------------------------------------------------
    # STEP 1: Suicidal keyword check — ALWAYS runs first
    # Never rely on ML for crisis detection
    # Better to over-flag than miss a real emergency
    # -------------------------------------------------------------------------
    for kw, weight in KEYWORDS.get("suicidal", []):
        if ' ' in kw:
            if re.search(r"\b" + re.escape(kw) + r"\b", txt) or \
               SequenceMatcher(None, kw, txt).ratio() >= PHRASE_FUZZY_THRESHOLD:
                return _build_result("suicidal", 0.99)
        else:
            if kw in tokens:
                return _build_result("suicidal", 0.99)
            for t in tokens:
                if SequenceMatcher(None, kw, t).ratio() >= TOKEN_FUZZY_THRESHOLD:
                    return _build_result("suicidal", 0.99)

    # -------------------------------------------------------------------------
    # STEP 2: ML classifier — primary detection
    # -------------------------------------------------------------------------
    try:
        from app.services.ml_classifier import classify_intent
        ml_result = classify_intent(text)
        ml_intent = ml_result["intent"]
        ml_confidence = ml_result["confidence"]

        # Neutral intent always returns Normal
        if ml_intent == "neutral":
            return _build_result("neutral", 0.3)

        # Uncertain — ML not confident enough, fall through to rule_intent.py
        if ml_intent == "uncertain":
            raise Exception("ML uncertain — trying rule_intent fallback")

        # Apply negative context multiplier
        neg_multiplier = _get_negative_context_multiplier(txt)
        ml_confidence = round(ml_confidence * neg_multiplier, 3)

        # Scale to our confidence range (0.3 - 0.99)
        scaled_confidence = 0.3 + 0.7 * ml_confidence
        scaled_confidence = round(min(0.98, scaled_confidence), 3)

        return _build_result(ml_intent, scaled_confidence)

    except Exception as e:
        # ML failed OR uncertain — fall through to rule_intent.py fallback
        pass

    # -------------------------------------------------------------------------
    # STEP 3: rule_intent.py fallback
    # Called when ML is unavailable (model not loaded, import error, etc.)
    # More sophisticated than old keyword scoring:
    # → has intensifier detection (sobrang, grabe, super)
    # → has Filipino stopword removal
    # → better keyword weights
    # → returns matched_keywords for debugging
    # -------------------------------------------------------------------------
    try:
        from app.services.rule_intent import analyze_with_rules
        rule_result = analyze_with_rules(text)

        rule_intent = rule_result.get("intent", "neutral")
        rule_confidence = rule_result.get("confidence", 0.3)
        rule_intensity = rule_result.get("intensity", 0.0)
        escalate = rule_result.get("escalate", False)

        # If rule_intent flagged suicidal escalation
        if escalate or rule_intent == "suicidal":
            return _build_result("suicidal", 0.99)

        # Neutral — no anxiety detected
        if rule_intent == "neutral":
            return _build_result("neutral", 0.3)

        # Apply negative context multiplier to rule-based confidence
        neg_multiplier = _get_negative_context_multiplier(txt)
        rule_confidence = round(rule_confidence * neg_multiplier, 3)

        # Use intensity to boost confidence if strong signals detected
        # intensity > 0.5 means multiple strong keywords matched
        # or intensifiers like "sobrang", "grabe" were present
        if rule_intensity > 0.5:
            rule_confidence = min(0.98, rule_confidence + (rule_intensity * 0.1))
            rule_confidence = round(rule_confidence, 3)

        # Scale to our confidence range
        scaled_confidence = 0.3 + 0.7 * rule_confidence
        scaled_confidence = round(min(0.98, scaled_confidence), 3)

        return _build_result(rule_intent, scaled_confidence)

    except Exception as e:
        # Both ML and rule_intent failed — return safe neutral
        pass

    # -------------------------------------------------------------------------
    # FINAL FALLBACK: both ML and rule_intent unavailable
    # Return neutral so GPT responds normally without anxiety context
    # -------------------------------------------------------------------------
    return _build_result("neutral", 0.3)


def _build_result(intent: str, confidence: float, post_crisis: bool = False) -> dict:
    """
    Maps intent + confidence to anxiety level, severity, and protocol.

    Confidence thresholds:
        < 0.45   → Normal
        0.45-0.60 → Low
        0.60-0.75 → Moderate
        0.75-0.98 → High
        >= 0.99   → Crisis
    """
    if confidence >= 0.99:
        return {
            "intent": intent,
            "confidence": confidence,
            "anxiety_level": "crisis",
            "severity": "High",
            "counselor_protocol": COUNSELOR_PROTOCOLS["crisis"],
            "crisis_resources": CRISIS_RESOURCES,
            "anxiety_score": 5,
        }

    if confidence >= 0.75:
        anxiety_level = "high"
        severity = "High"
        anxiety_score = 5
        protocol = COUNSELOR_PROTOCOLS["high"]
    elif confidence >= 0.60:
        anxiety_level = "moderate"
        severity = "Moderate"
        anxiety_score = 3
        protocol = COUNSELOR_PROTOCOLS["moderate"]
    elif confidence >= 0.45:
        anxiety_level = "low"
        severity = "Low"
        anxiety_score = 1
        protocol = COUNSELOR_PROTOCOLS["low"]
    else:
        anxiety_level = None
        anxiety_score = 0
        protocol = None

        if post_crisis:
            severity = "Low"
            anxiety_level = "low"
            anxiety_score = 1
            protocol = COUNSELOR_PROTOCOLS["low"]
        else:
            severity = "Normal"

    return {
        "intent": intent,
        "confidence": confidence,
        "anxiety_level": anxiety_level,
        "severity": severity,
        "counselor_protocol": protocol,
        "crisis_resources": None,
        "anxiety_score": anxiety_score,
    }