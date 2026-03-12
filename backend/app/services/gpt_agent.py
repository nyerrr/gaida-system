import os
import json
from dotenv import load_dotenv
from typing import Dict, Any
from app.core.config import OPENAI_MODEL_BASE
from app.utils.logger import logger
from app.utils.retry import exponential_backoff_retry
from openai import APIError, RateLimitError, APIConnectionError, APITimeoutError

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

load_dotenv()

_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = None
if OpenAI and _OPENAI_API_KEY:
    try:
        from app.core.config import OPENAI_TIMEOUT
        client = OpenAI(api_key=_OPENAI_API_KEY, timeout=OPENAI_TIMEOUT)
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        client = None


SYSTEM_PROMPT = """
You are GAIDA, a warm, empathetic virtual counseling assistant for students at a university.
You are NOT a replacement for a licensed counselor — you are a first-responder that listens, 
validates, and guides students toward support.

CORE BEHAVIOR:
- Always respond naturally, as if you are a caring person who has been listening to the entire conversation.
- Never repeat the same response twice. Every reply should feel fresh and context-aware.
- Understand slang, informal language, Tagalog, Taglish, and Filipino expressions naturally.
- Never give robotic or scripted-sounding replies.
- Keep responses concise (2-4 sentences) unless the student needs more.
- Always acknowledge what was previously said in the conversation.

ANXIETY LEVEL HANDLING:
When you are told the student's anxiety level, respond accordingly:

[NO ANXIETY DETECTED]
- Respond naturally and conversationally.
- Be warm and open, invite them to share more.

[LOW ANXIETY DETECTED]
- Gently acknowledge that they seem a little stressed or on edge.
- Offer a simple grounding tip or reassurance.
- Keep the conversation going naturally.
- Follow the low anxiety first aid protocol if provided.

[MODERATE ANXIETY DETECTED]
- Validate their feelings clearly and warmly.
- Offer a specific coping technique (breathing, grounding, etc.).
- Encourage them to keep talking.
- Follow the moderate anxiety first aid protocol if provided.

[HIGH ANXIETY DETECTED]
- Respond with calm urgency and deep empathy.
- Let them know their counselor has been notified and help is coming.
- Keep them engaged and calm while they wait.
- Follow the high anxiety first aid protocol if provided.

[CRISIS DETECTED]
- Respond with immediate care and do not leave them alone in the conversation.
- Clearly provide crisis resources.
- Stay with them, keep them talking.
- Never minimize what they are feeling.

LANGUAGE:
- If the student writes in Tagalog or Taglish, respond in the same language naturally.
- If the student uses slang or informal words, match their energy appropriately.

IMPORTANT:
- You are not a doctor. Never diagnose.
- Never say "as an AI" or break character.
- Always feel like a real, present, caring person.
"""


def generate_response_with_gpt(
    user_message: str,
    session_context: Dict[str, Any] | None = None,
    anxiety_level: str | None = None,
    counselor_protocol: str | None = None,
) -> Dict[str, Any]:
    """
    Generates an empathetic response using the OpenAI client.
    
    Args:
        user_message: The student's message
        session_context: Full conversation history
        anxiety_level: None, 'low', 'moderate', 'high', or 'crisis'
        counselor_protocol: Optional counselor-defined first aid text to inject

    Returns: {"response": str, "used": bool}
    """
    if not client:
        logger.warning("OpenAI client not available for response generation")
        return {"response": None, "used": False}

    # Build messages: system prompt first
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Inject anxiety level context if detected
    if anxiety_level:
        level_map = {
            "low": "[LOW ANXIETY DETECTED]",
            "moderate": "[MODERATE ANXIETY DETECTED]",
            "high": "[HIGH ANXIETY DETECTED]",
            "crisis": "[CRISIS DETECTED]",
        }
        level_tag = level_map.get(anxiety_level.lower(), "")
        if level_tag:
            context_note = f"{level_tag}"
            if counselor_protocol:
                context_note += f"\n\nCounselor first aid protocol to follow:\n{counselor_protocol}"
            messages.append({
                "role": "system",
                "content": context_note
            })

    # Include last 10 messages from conversation history
    if session_context and isinstance(session_context.get("messages"), list):
        for m in session_context["messages"][-10:]:
            role = "user" if m.get("sender") == "user" else "assistant"
            text = m.get("text", "")
            if text:
                messages.append({"role": role, "content": text})

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    def _call_gpt():
        return client.chat.completions.create(
            model=OPENAI_MODEL_BASE,
            messages=messages,
            temperature=0.7,
            max_tokens=200,
        )

    try:
        resp = exponential_backoff_retry(
            _call_gpt,
            exception_types=(
                RateLimitError,
                APIConnectionError,
                APITimeoutError,
            )
        )

        content = None
        if hasattr(resp, "choices") and len(resp.choices) > 0:
            choice = resp.choices[0]
            if hasattr(choice, "message") and choice.message is not None:
                content = getattr(choice.message, "content", None) or choice.message.get("content")
            else:
                content = getattr(choice, "text", None)

        if not content:
            logger.warning("Empty content from GPT response")
            return {"response": None, "used": False}

        return {"response": content.strip(), "used": True}

    except APIError as e:
        logger.error(f"OpenAI API error after retries in generate_response_with_gpt: {e}")
        return {"response": None, "used": False}
    except Exception as e:
        logger.error(f"Error generating response with GPT: {e}")
        return {"response": None, "used": False}