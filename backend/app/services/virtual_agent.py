import re
from typing import Tuple
from difflib import SequenceMatcher

# Fuzzy matching thresholds and multipliers (tunable)
PHRASE_FUZZY_THRESHOLD = 0.70
TOKEN_FUZZY_THRESHOLD = 0.82
FUZZY_WEIGHT_MULTIPLIER = 0.9


RESPONSES = {
    "anxiety": "I understand that you're feeling anxious. Let's take this one step at a time.",
    "sadness": "I'm here to listen. Would you like to talk more about what's making you feel this way?",
    "stress": "It sounds like you're under a lot of pressure. Taking short breaks can sometimes help.",
}

# Keywords with simple weights. Weights reflect signal strength (higher = stronger indicator).
# Add or tune these lists as you expand the lexicon.
KEYWORDS = {
    "suicidal": [
        ("gusto ko na mamatay", 3.5), ("ayoko na mabuhay", 3.5), ("magpapakamatay", 3.5),
        ("tapusin ko na", 3.5), ("i want to die", 3.5), ("kill myself", 3.5), ("suicide", 3.5)
    ],
    "anxiety": [
        ("panic", 1.5), ("panic attack", 2.0), ("anxiety", 1.5), ("anxious", 1.5), ("nervous", 1.0),
        ("nahihirapan", 1.2), ("natataranta", 1.3), ("di makatulog", 1.0), ("hopeless", 2.5),
        # spelling/slang variants
        ("panicattack", 1.8), ("panicked", 1.4), ("nakakatakot", 1.2), ("nababalisa", 1.2),
    ],
    "sadness": [
        ("sad", 1.2), ("malungkot", 1.5), ("wala nang gana", 2.5), ("hopeless", 2.0),
        ("cry", 1.0), ("iyak", 1.0), ("di na kaya", 2.0),
        # variants/slang
        ("wala akong gana", 2.3), ("wala na akong gana", 2.3), ("ayoko na", 2.2),
    ],
    "stress": [
        ("stress", 1.5), ("stressed", 1.5), ("pressure", 1.2), ("pagod", 1.3),
        ("nakakapagod", 1.5), ("pagod na ko", 1.8), ("pagod na ako", 1.8), ("di ko na kaya", 2.0),
        ("nakakapgod", 1.2), ("nakaka pagod", 1.2), ("pagod na", 1.6),
    ],
}


def _normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # Lowercase, normalize whitespace, remove excessive punctuation
    txt = text.lower()
    txt = re.sub(r"[\u2018\u2019\u201c\u201d]", "'", txt)
    txt = re.sub(r"[^\w\s']+", ' ', txt)
    txt = re.sub(r"\s+", ' ', txt).strip()
    return txt


def _tokenize(text: str):
    # simple word tokens (keeps tagalog/taglish tokens intact)
    return re.findall(r"\w+'?\w*|\w+", text)


def detect_intent_from_text(text: str) -> Tuple[str, float]:
    """Return (best_intent, confidence) for a raw text input.

    Confidence is normalized per-intent: matched_weight / max_possible_weight, mapped
    into [0.3, 1.0] to avoid overconfidence on sparse matches.
    """
    txt = _normalize_text(text)
    tokens = set(_tokenize(txt))

    # Quick escalation check for suicidal phrases (exact or fuzzy)
    for kw, weight in KEYWORDS.get("suicidal", []):
        if ' ' in kw:
            if re.search(r"\b" + re.escape(kw) + r"\b", txt) or SequenceMatcher(None, kw, txt).ratio() >= PHRASE_FUZZY_THRESHOLD:
                return ("suicidal", 0.99)
        else:
            if kw in tokens:
                return ("suicidal", 0.99)
            for t in tokens:
                if SequenceMatcher(None, kw, t).ratio() >= TOKEN_FUZZY_THRESHOLD:
                    return ("suicidal", 0.99)

    best_intent = None
    best_score = 0.0
    best_max = 1.0

    for intent, kw_list in KEYWORDS.items():
        matched_weight = 0.0
        max_possible = sum(w for _, w in kw_list) or 1.0

        for kw, weight in kw_list:
            # match multi-word keywords as whole phrases, single-word via token set
            if ' ' in kw:
                # exact phrase match
                if re.search(r"\b" + re.escape(kw) + r"\b", txt):
                    matched_weight += weight
                else:
                    # fuzzy phrase match against whole text (handles simple misspellings)
                    if SequenceMatcher(None, kw, txt).ratio() >= PHRASE_FUZZY_THRESHOLD:
                        matched_weight += weight * FUZZY_WEIGHT_MULTIPLIER
            else:
                if kw in tokens:
                    matched_weight += weight
                else:
                    # fuzzy token match against tokens
                    for t in tokens:
                        # require a reasonably high similarity for single-word matches
                        if SequenceMatcher(None, kw, t).ratio() >= TOKEN_FUZZY_THRESHOLD:
                            matched_weight += weight * FUZZY_WEIGHT_MULTIPLIER
                            break

        if matched_weight > best_score:
            best_score = matched_weight
            best_max = max_possible
            best_intent = intent

    normalized = best_score / best_max if best_max > 0 else 0.0
    # map normalized into [0.3, 1.0]
    confidence = 0.3 + 0.7 * min(1.0, normalized)
    if best_intent is None:
        return ("unknown", 0.0)
    return (best_intent, round(confidence, 3))


def generate_response(intent_data: dict):
    """Generate a response.

    Backwards-compatible behavior:
    - If `intent_data` is a dict containing `intent`, the original response mapping is used.
    - If `intent_data` contains `text`, we run a lightweight detection and return the mapped response.
      If `return_meta` is True, a dict with `response`, `intent`, and `confidence` is returned.
    - If a plain string is passed, it's treated as raw text and analyzed.
    """
    # Input is already an intent dict (legacy behavior)
    if isinstance(intent_data, dict) and 'intent' in intent_data:
        intent = intent_data.get('intent')
        if intent in RESPONSES:
            return RESPONSES[intent]

    # If a dict with raw text is provided
    if isinstance(intent_data, dict) and 'text' in intent_data:
        text = intent_data.get('text', '')
        intent, confidence = detect_intent_from_text(text)
        response = RESPONSES.get(intent, "I'm here with you. Please tell me more.")
        if intent_data.get('return_meta'):
            return {'response': response, 'intent': intent, 'confidence': confidence}
        return response

    # If a plain string was passed, analyze it
    if isinstance(intent_data, str):
        intent, _ = detect_intent_from_text(intent_data)
        return RESPONSES.get(intent, "I'm here with you. Please tell me more.")

    # Fallback
    return "I'm here with you. Please tell me more."

