def classify_anxiety(sentiment_score: float, keyword_score: int):
    """
    Rule-based anxiety classification (prototype).
    """
    if keyword_score >= 2:
        level = "HIGH"
        confidence = 0.85
    elif keyword_score == 1 or sentiment_score < -0.4:
        level = "MODERATE"
        confidence = 0.70
    else:
        level = "LOW"
        confidence = 0.60

    return level, confidence