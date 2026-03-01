"""
intent_model.py
---------------
Uses the fine-tuned GPT-3.5-turbo model for mental health intent detection.

Labels: anxiety, sadness, stress, neutral, suicidal

Usage:
    from app.services.intent_model import predict_intent
"""

import json
from app.services.openai_client import client
from app.utils.logger import logger
from app.utils.retry import exponential_backoff_retry
from openai import APIError, RateLimitError, APIConnectionError, APITimeoutError

# Your fine-tuned model ID
FINE_TUNED_MODEL = "ft:gpt-3.5-turbo-0125:personal::DDu4xxxR"

SYSTEM_PROMPT = """
You are an intent classification system for a university mental health support chatbot.

Task:
Classify the emotional intent of the user's message.

Rules:
- Return ONLY valid JSON
- Do NOT explain
- Do NOT give advice

Allowed labels:
anxiety
sadness
stress
neutral
suicidal

JSON format:
{
  "intent": "label",
  "confidence": 0.0
}
"""

def predict_intent(user_input: str) -> dict:
    if not user_input or not user_input.strip():
        return {"intent": "neutral", "confidence": 0.5}

    def _call_model():
        """Inner function to call model with retry logic."""
        return client.chat.completions.create(
            model=FINE_TUNED_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input},
            ],
            temperature=0,
            max_tokens=60,
        )

    try:
        # Retry on transient errors
        response = exponential_backoff_retry(
            _call_model,
            exception_types=(
                RateLimitError,
                APIConnectionError,
                APITimeoutError,
            )
        )

        content = response.choices[0].message.content.strip()
        result = json.loads(content)
        intent = result.get("intent", "neutral")

        # ---- Practical approach: map confidence based on intent ----
        confidence_map = {
            "neutral": 0.6,
            "anxiety": 0.9,
            "stress": 0.85,
            "sadness": 0.85,
            "suicidal": 0.95,
        }
        confidence = confidence_map.get(intent, 0.8)  # default 0.8

        return {
            "intent": intent,
            "confidence": round(confidence, 2)
        }

    except APIError as e:
        logger.error(f"OpenAI API error after retries in predict_intent: {e}")
        return {"intent": "neutral", "confidence": 0.5, "error": str(e)}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse model response as JSON: {e}")
        return {"intent": "neutral", "confidence": 0.5, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in predict_intent: {e}")
        return {"intent": "neutral", "confidence": 0.5, "error": str(e)}


if __name__ == "__main__":
    # Quick test
    test_inputs = [
        "I feel so anxious about everything",
        "Malungkot na malungkot ako",
        "Pagod na pagod na ako sa deadlines",
        "Gusto ko na mamatay",
        "Good morning, I feel fine today"
    ]
    print("\n=== Sample Predictions ===")
    for text in test_inputs:
        result = predict_intent(text)
        print(f"Input:  {text}")
        print(f"Intent: {result['intent']} ({result['confidence']})")
        print()