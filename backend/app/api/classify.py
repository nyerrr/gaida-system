from fastapi import APIRouter, UploadFile, File
from app.api.schemas import TextInput
from app.nlp.sentiment import get_sentiment
from app.nlp.keywords import keyword_score
from app.ml.anxiety_model import classify_anxiety
import speech_recognition as sr
from io import BytesIO

router = APIRouter(prefix="/api", tags=["classify"])

@router.post("/classify-anxiety")
def classify(payload: TextInput):
    sentiment = get_sentiment(payload.text)
    kw_score = keyword_score(payload.text)
    
    anxiety_level, confidence = classify_anxiety(sentiment, kw_score)

    return {
        "sentiment_score": sentiment,
        "keyword_score": kw_score,
        "anxiety_level": anxiety_level,
        "confidence": confidence
    }

@router.post("/classify-anxiety-audio")
async def classify_audio(file: UploadFile = File(...)):
    """Classify anxiety from audio file"""
    recognizer = sr.Recognizer()
    
    audio_data = await file.read()
    audio_file = BytesIO(audio_data)
    
    with sr.AudioFile(audio_file) as source:
        audio = recognizer.record(source)
    
    try:
        text = recognizer.recognize_google(audio)
        sentiment = get_sentiment(text)
        kw_score = keyword_score(text)
        anxiety_level, confidence = classify_anxiety(sentiment, kw_score)
        
        return {
            "transcribed_text": text,
            "sentiment_score": sentiment,
            "keyword_score": kw_score,
            "anxiety_level": anxiety_level,
            "confidence": confidence
        }
    except sr.UnknownValueError:
        return {"error": "Could not understand audio"}