hookup_keywords = {
    "low": ["nervous", "kinakabahan", "tense"],
    "moderate": ["di makafocus", "nahihirapan"],
    "high": ["hindi ko na kaya", "ayoko na"]
}

def keyword_score(text: str):
    score = 0
    for level, words in hookup_keywords.items():
        for w in words:
            if w in text:
                score += 1
    return score
