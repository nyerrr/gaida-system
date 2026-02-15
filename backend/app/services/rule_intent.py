import re
from typing import Dict, List
from difflib import SequenceMatcher

# fuzzy thresholds for rule-based matching (align with virtual_agent tuning)
PHRASE_FUZZY_THRESHOLD = 0.70
TOKEN_FUZZY_THRESHOLD = 0.82

STOPWORDS = {
    "ang", "ng", "sa", "ako", "ikaw", "siya",
    "ko", "mo", "niya", "na", "pa", "lang",
    "yung", "ito", "yan", "din", "rin"
}

KEYWORDS = {
    "suicidal": [
        "ayoko na mabuhay",
        "gusto ko na mamatay",
        "magpapakamatay",
        "tapusin ko na",
        "wala nang dahilan para mabuhay",
        "i want to die",
        "kill myself",
        "end my life",
        "suicide"
    ],

    "anxiety": [
        "anxious", "anxiety", "nervous", "panic",
        "worried", "restless", "uneasy",
        "kinakabahan", "kabado", "natatakot",
        "natataranta", "balisa",
        "overthink", "overthinking"
    ],

    "sadness": [
        "sad", "depressed", "depression",
        "hopeless", "lonely", "empty",
        "worthless", "crying",
        "malungkot", "lungkot",
        "kawalan ng pag asa",
        "walang halaga",
        "wala akong gana",
        "di na kaya"
    ],

    "stress": [
        "stressed", "stress",
        "overwhelmed", "pressure",
        "burnout", "drained",
        "exhausted",
        "pagod", "napapagod",
        "naiistress"
    ],
}


INTENSIFIERS = {
    "sobrang", "sobra", "grabe", "super",
    "too much", "napaka"
}

ESCALATION_MESSAGE = (
    "If you or someone else is in immediate danger, please contact local emergency services "
    "or a trusted person. If you're feeling like harming yourself, reach out to a crisis line "
    "or a mental health professional."
)


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"(.)\1{2,}", r"\1", text)
    return text


def remove_stopwords(text: str) -> str:
    tokens = text.split()
    filtered = [t for t in tokens if t not in STOPWORDS]
    return " ".join(filtered)


def analyze_with_rules(user_input: str) -> Dict[str, object]:
    raw_text = user_input or ""
    text = normalize_text(raw_text)
    text = remove_stopwords(text)

    counts = {label: 0 for label in KEYWORDS}
    matched: Dict[str, List[str]] = {label: [] for label in KEYWORDS}

    for label, words in KEYWORDS.items():
        for w in words:
            pattern = r"\b" + re.escape(w) + r"\b"
            if re.search(pattern, text):
                counts[label] += 1
                matched[label].append(w)
            else:
                # fuzzy phrase/token matching fallback
                if ' ' in w:
                    # compare phrase similarity against full text
                    if SequenceMatcher(None, w, text).ratio() >= PHRASE_FUZZY_THRESHOLD:
                        counts[label] += 1
                        matched[label].append(w + " (fuzzy)")
                else:
                    # token-wise similarity check
                    tokens = set(text.split())
                    for t in tokens:
                        if SequenceMatcher(None, w, t).ratio() >= TOKEN_FUZZY_THRESHOLD:
                            counts[label] += 1
                            matched[label].append(w + " (fuzzy->" + t + ")")
                            break

    total_hits = sum(counts.values())

    # Urgent escalation: if suicidal keywords are present, prioritize immediately
    if matched.get('suicidal'):
        return {
            "intent": "suicidal",
            "confidence": 0.99,
            "intensity": 1.0,
            "matched_keywords": {"suicidal": matched['suicidal']},
            "escalate": True,
            "escalation_message": ESCALATION_MESSAGE
        }

    if total_hits == 0:
        return {
            "intent": "neutral",
            "confidence": 0.5,
            "intensity": 0.0,
            "matched_keywords": {}
        }

    best_label = max(counts, key=counts.get)
    best_count = counts[best_label]

    confidence = best_count / total_hits

    intensity_score = best_count

    for intensifier in INTENSIFIERS:
        if intensifier in text:
            intensity_score += 1

    intensity = min(1.0, intensity_score / 5)

    return {
        "intent": best_label,
        "confidence": round(confidence, 3),
        "intensity": round(intensity, 3),
        "matched_keywords": {
            best_label: matched[best_label]
        }
    }