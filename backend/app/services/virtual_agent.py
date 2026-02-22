import re
import random
from typing import Tuple
from difflib import SequenceMatcher

PHRASE_FUZZY_THRESHOLD = 0.70
TOKEN_FUZZY_THRESHOLD = 0.82
FUZZY_WEIGHT_MULTIPLIER = 0.9

# Multiple responses per intent - randomly selected to avoid repetition
RESPONSES = {
    "faq": [
        "GAIDA is a virtual counseling assistant for students. You can share how you're feeling, talk about stress, anxiety, or sadness, and get support anytime. Your counselor can also view sessions to follow up with you.",
        "This app is here to support your mental and emotional wellbeing. Talk to me about what you're feeling, and I'll listen. For urgent concerns, your school counselor is notified.",
        "GAIDA helps students express and manage their emotions in a safe space. You can share anything on your mind, and I'll respond with support and coping tips.",
    ],
    "anxiety": [
        "It sounds like you're feeling anxious right now. That's okay. Let's slow down together. Can you tell me what's been on your mind?",
        "Anxiety can feel overwhelming, but you don't have to face it alone. What's been worrying you the most lately?",
        "I hear you. When anxiety hits, even small things can feel heavy. Take a breath with me. What's making you feel this way?",
        "Feeling anxious is tough, especially when it feels constant. Would you like to talk about what's triggering it?",
        "You're not alone in this. A lot of students go through this. Can you describe what the anxiety feels like for you?",
    ],
    "sadness": [
        "I'm really sorry you're feeling this way. Your feelings are valid. Would you like to talk about what's been going on?",
        "It takes courage to share how you feel. I'm here and I'm listening. What's been making you feel sad?",
        "Sadness can feel isolating, but you don't have to carry it alone. What's been weighing on you?",
        "I hear how much pain you're in right now. You matter and what you feel matters. Can you tell me more?",
        "Sometimes sadness creeps in without a clear reason. That's okay. I'm here with you. What's on your heart right now?",
    ],
    "stress": [
        "It sounds like you have a lot on your plate right now. That kind of pressure is exhausting. What's been the hardest part?",
        "School stress is real and it can pile up fast. You don't have to handle everything at once. What's stressing you out the most?",
        "Feeling burned out is a sign you've been pushing yourself too hard. Let's talk about what's overwhelming you.",
        "Deadlines, requirements, expectations. It's a lot. I hear you. What would help you feel even a little lighter right now?",
        "When everything feels urgent at once, it's hard to breathe. Let's slow down. What's the biggest thing you're carrying today?",
    ],
    "suicidal": [
        "I'm very concerned about what you just shared. Your life has value and you matter deeply. Please reach out to a counselor or someone you trust right now. You are not alone in this.",
        "Thank you for trusting me with this. I want you to be safe. Please talk to a counselor or call a crisis line immediately. You deserve support.",
        "What you're feeling is serious and I want to make sure you're okay. Please reach out to the guidance office or a trusted person right now. You don't have to go through this alone.",
    ],
    "neutral": [
        "Hi! I'm GAIDA, your virtual counseling assistant. I'm here to listen and support you. How are you feeling today?",
        "Hello! This is a safe space where you can talk about anything on your mind. How can I help you today?",
        "I'm here for you. This app is designed to support students with their mental and emotional wellbeing. Feel free to share anything.",
        "Welcome! You can talk to me about how you're feeling, what's stressing you out, or anything that's been on your mind. What brings you here today?",
    ],
    "other": [
        "I'm here and I'm listening. Could you tell me more about how you're feeling?",
        "I want to understand what you're going through. Can you share a little more?",
        "Thank you for reaching out. I'm here with you. What's on your mind?",
    ],
    "unknown": [
        "I'm here with you. Feel free to share what's on your mind.",
        "I want to help. Can you tell me a bit more about how you're feeling today?",
        "You can talk to me. I'm listening.",
    ],
}

KEYWORDS = {
    "suicidal": [
        ("gusto ko na mamatay", 3.5), ("ayoko na mabuhay", 3.5), ("magpapakamatay", 3.5),
        ("tapusin ko na", 3.5), ("i want to die", 3.5), ("kill myself", 3.5), ("suicide", 3.5),
        ("end my life", 3.5), ("wala na akong dahilan", 3.0), ("gusto ko nang mawala", 3.5),
        ("pagod na ako mabuhay", 3.5), ("sana wala na lang ako", 3.5),
    ],
    "anxiety": [
        ("panic", 1.5), ("panic attack", 2.0), ("anxiety", 1.5), ("anxious", 1.5), ("nervous", 1.0),
        ("nahihirapan", 1.2), ("natataranta", 1.3), ("di makatulog", 1.0),
        ("panicattack", 1.8), ("panicked", 1.4), ("nakakatakot", 1.2), ("nababalisa", 1.2),
        ("kinakabahan", 1.5), ("kabado", 1.5), ("balisa", 1.3), ("nag aalala", 1.4),
        ("overthink", 1.3), ("overthinking", 1.3), ("kaba", 1.2), ("takot", 1.0),
        ("natatakot", 1.3), ("nerbyos", 1.2), ("mapanatag", 1.1),
    ],
    "sadness": [
        ("sad", 1.2), ("malungkot", 1.5), ("wala nang gana", 2.5),
        ("cry", 1.0), ("iyak", 1.0), ("di na kaya", 2.0),
        ("wala akong gana", 2.3), ("wala na akong gana", 2.3), ("ayoko na", 2.2),
        ("lungkot", 1.4), ("hopeless", 2.0), ("worthless", 1.8), ("empty", 1.5),
        ("alone", 1.2), ("lonely", 1.5), ("depressed", 1.8), ("depression", 1.8),
        ("wala akong halaga", 2.0), ("naiiyak", 1.3), ("broken", 1.4),
        ("unloved", 1.5), ("invisible", 1.3), ("abandoned", 1.5),
    ],
    "stress": [
        ("stress", 1.5), ("stressed", 1.5), ("pressure", 1.2), ("pagod", 1.3),
        ("nakakapagod", 1.5), ("pagod na ko", 1.8), ("pagod na ako", 1.8), ("di ko na kaya", 2.0),
        ("nakakapgod", 1.2), ("nakaka pagod", 1.2), ("pagod na", 1.6),
        ("burnout", 1.8), ("burnt out", 1.8), ("overwhelmed", 1.5), ("exhausted", 1.5),
        ("deadlines", 1.4), ("requirements", 1.2), ("overloaded", 1.5), ("drained", 1.4),
        ("ubos na", 1.5), ("wala nang time", 1.5), ("walang pahinga", 1.4),
        ("sabog", 1.3), ("busy", 1.1), ("kulang sa tulog", 1.5),
    ],
}


def _normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    txt = text.lower()
    txt = re.sub(r"[\u2018\u2019\u201c\u201d]", "'", txt)
    txt = re.sub(r"[^\w\s']+", ' ', txt)
    txt = re.sub(r"\s+", ' ', txt).strip()
    return txt


def _tokenize(text: str):
    return re.findall(r"\w+'?\w*|\w+", text)


def _get_response(intent: str) -> str:
    options = RESPONSES.get(intent, RESPONSES["unknown"])
    return random.choice(options)


def detect_intent_from_text(text: str) -> Tuple[str, float]:
    txt = _normalize_text(text)
    tokens = set(_tokenize(txt))

    # Suicidal escalation check first
    for kw, weight in KEYWORDS.get("suicidal", []):
        if ' ' in kw:
            if re.search(r"\b" + re.escape(kw) + r"\b", txt) or \
               SequenceMatcher(None, kw, txt).ratio() >= PHRASE_FUZZY_THRESHOLD:
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
            if ' ' in kw:
                if re.search(r"\b" + re.escape(kw) + r"\b", txt):
                    matched_weight += weight
                elif SequenceMatcher(None, kw, txt).ratio() >= PHRASE_FUZZY_THRESHOLD:
                    matched_weight += weight * FUZZY_WEIGHT_MULTIPLIER
            else:
                if kw in tokens:
                    matched_weight += weight
                else:
                    for t in tokens:
                        if SequenceMatcher(None, kw, t).ratio() >= TOKEN_FUZZY_THRESHOLD:
                            matched_weight += weight * FUZZY_WEIGHT_MULTIPLIER
                            break

        if matched_weight > best_score:
            best_score = matched_weight
            best_max = max_possible
            best_intent = intent

    normalized = best_score / best_max if best_max > 0 else 0.0
    confidence = 0.3 + 0.7 * min(1.0, normalized)

    if best_intent is None or best_score == 0.0:
        return ("neutral", 0.5)

    return (best_intent, round(confidence, 3))


def generate_response(intent_data: dict):
    # Intent dict (from router)
    if isinstance(intent_data, dict) and 'intent' in intent_data:
        intent = intent_data.get('intent')
        return _get_response(intent)

    # Dict with raw text
    if isinstance(intent_data, dict) and 'text' in intent_data:
        text = intent_data.get('text', '')
        intent, confidence = detect_intent_from_text(text)
        response = _get_response(intent)
        if intent_data.get('return_meta'):
            return {'response': response, 'intent': intent, 'confidence': confidence}
        return response

    # Plain string
    if isinstance(intent_data, str):
        intent, _ = detect_intent_from_text(intent_data)
        return _get_response(intent)

    return _get_response("unknown")