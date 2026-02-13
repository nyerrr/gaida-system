INTENT_ANXIETY_MAP = {
    "panic": 5,
    "severe anxiety": 5,
    "anxiety": 5,
    "stress": 3,
    "overwhelm": 3,
    "neutral": 1,
    "positive": 0,
    "happy": 0,
}

def score_anxiety(intent: str) -> int:
    return INTENT_ANXIETY_MAP.get(intent.lower(), 1)