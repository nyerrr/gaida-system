import json
from typing import Dict, Any
from app.services.openai_client import client
from backend.app.core.config import OPENAI_FINETUNED_MODEL
from app.utils.logger import logger
from app.utils.retry import exponential_backoff_retry
from openai import APIError, RateLimitError, APIConnectionError, APITimeoutError

SYSTEM_PROMPT = """
You are an intent classification system for a university mental health support chatbot.

Task:
Classify the emotional intent of the user's message.

Rules:
- Return ONLY valid JSON
- No explanations
- No extra text

Allowed labels:
anxiety
sadness
stress
neutral
other

JSON format:
{
  "intent": "label",
  "confidence": 0.0
}
"""

ALLOWED_INTENTS = {"anxiety", "sadness", "stress", "neutral", "other"}


def _validate_intent_response(data: Any) -> Dict[str, Any]:
    """
    Validate and sanitize intent response from model.
    
    Args:
        data: Parsed JSON data from model response
        
    Returns:
        Valid intent dict with intent and confidence keys
        
    Raises:
        ValueError: If data doesn't match expected schema
    """
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict, got {type(data).__name__}")
    
    intent = data.get("intent", "").strip()
    if not intent or intent not in ALLOWED_INTENTS:
        raise ValueError(f"Invalid intent '{intent}'. Allowed: {ALLOWED_INTENTS}")
    
    try:
        confidence = float(data.get("confidence", 0.5))
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid confidence value: {e}")
    
    # Clamp confidence to [0.0, 1.0]
    confidence = max(0.0, min(1.0, confidence))
    
    return {"intent": intent, "confidence": confidence}


def analyze_with_gpt(user_input: str) -> Dict[str, Any]:
    """
    Analyze user input intent using GPT fine-tuned model.
    
    Args:
        user_input: User message text
        
    Returns:
        Dict with 'intent' (str) and 'confidence' (float in [0.0, 1.0])
    """
    if not client:
        logger.warning("OpenAI client not available")
        return {"intent": "other", "confidence": 0.5}

    def _call_gpt():
        """Inner function to call OpenAI with retry logic."""
        return client.chat.completions.create(
            model=OPENAI_FINETUNED_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input},
            ],
            temperature=0,
            response_format={"type": "json_object"},
            max_tokens=50,
        )

    try:
        # Retry on transient errors
        response = exponential_backoff_retry(
            _call_gpt,
            exception_types=(
                RateLimitError,
                APIConnectionError,
                APITimeoutError,
            )
        )

        content = response.choices[0].message.content
        
        # Attempt to parse JSON
        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse model response as JSON: {e}. Content: {content}")
            return {"intent": "other", "confidence": 0.5}
        
        # Validate schema and values
        try:
            validated = _validate_intent_response(result)
            return validated
        except ValueError as e:
            logger.error(f"Invalid intent response schema: {e}. Data: {result}")
            return {"intent": "other", "confidence": 0.5}

    except APIError as e:
        logger.error(f"OpenAI API error after retries: {e}")
        return {"intent": "other", "confidence": 0.5}
    except Exception as e:
        logger.error(f"Intent detection error: {e}")
        return {"intent": "other", "confidence": 0.5}