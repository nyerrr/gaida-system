from fastapi import APIRouter
from app.nlp.sentiment import get_sentiment
from pydantic import BaseModel

router = APIRouter(prefix="/text", tags=["text"])

class AnxietyRequest(BaseModel):
    text: str
    keyword_score: int = 0

def derive_anxiety(sentiment, keyword_score):
    if keyword_score >= 2:
        return "HIGH"
    elif keyword_score == 1 or sentiment < -0.4:
        return "MODERATE"
    else:
        return "LOW"

@router.post("/analyze")
def analyze_text(text: str):
    sentiment = get_sentiment(text)
    keyword_score = 0  # Your keyword scoring logic here
    anxiety_level = derive_anxiety(sentiment, keyword_score)
    
    return {
        "text": text,
        "sentiment": sentiment,
        "anxiety": anxiety_level
    }

@router.post("/classify-anxiety")
def classify_anxiety(request: AnxietyRequest):
    sentiment = get_sentiment(request.text)
    
    # Taglish-aware fallback heuristic
    if sentiment == 0 and request.keyword_score > 0:
        sentiment = -0.5
    
    anxiety_level = derive_anxiety(sentiment, request.keyword_score)
    
    return {
        "sentiment_score": sentiment,
        "keyword_score": request.keyword_score,
        "anxiety_level": anxiety_level
    }
