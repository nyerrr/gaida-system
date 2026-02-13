from typing import Dict

KEYWORDS = {
    "anxiety": [
        "anxious", "anxiety", "nervous", "panic", "worried",
        "kinakabahan", "takot", "natataranta"
    ],
    "sadness": [
        "sad", "depressed", "hopeless", "lonely", "down", "malungkot",
        "wala", "naubusan", "di na"
    ],
    "stress": [
        "stressed", "overwhelmed", "pressure", "burnout", "tense", "stress",
        "pagod",
    ],
}


def analyze_with_rules(user_input: str) -> Dict[str, object]:
    """
    Return a dict: {"intent": <label>, "confidence": <0.0-1.0>}
    Basic keyword counting across categories; returns 'neutral' when nothing found.
    """
    text = (user_input or "").lower()
    counts = {label: 0 for label in KEYWORDS}

    for label, words in KEYWORDS.items():
        for w in words:
            if w in text:
                counts[label] += 1

    total_hits = sum(counts.values())
    if total_hits == 0:
        return {"intent": "neutral", "confidence": 0.5}

    best_label = max(counts, key=counts.get)
    best_count = counts[best_label]

    confidence = 0.5 + min(0.5, best_count / max(1, total_hits))

    return {"intent": best_label if best_count > 0 else "other", "confidence": round(confidence, 3)}
