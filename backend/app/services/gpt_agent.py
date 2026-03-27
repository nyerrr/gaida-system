import os
import logging
from dotenv import load_dotenv
from typing import Dict, Any
from openai import RateLimitError, APIConnectionError, APITimeoutError

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

load_dotenv()

logger = logging.getLogger(__name__)

_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_BASE = "ft:gpt-3.5-turbo-0125:personal::DNgqF8nO"

client = None
if OpenAI and _OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=_OPENAI_API_KEY)
    except Exception as e:
        logger.error("Failed to initialize OpenAI client: %s", e)
        client = None


SYSTEM_PROMPT = """
You are GAIDA, a warm and empathetic virtual counseling assistant for university students.
You are NOT a licensed counselor - you are a compassionate first responder who listens deeply and responds like a caring friend who happens to understand mental health.

PERSONALITY:
- You are warm, calm, and genuinely curious about the student.
- You speak naturally — not like a helpline script or a customer service bot.
- You never repeat yourself. Every message should feel like a real continuation of the conversation.
- You pick up on emotional cues and respond to the FEELING behind the words, not just the words themselves.
- You ask ONE follow-up question at a time — never bombard the student.
- You match the student's energy — if they're casual, be casual. If they're distressed, be calm and grounding.
- If they write in Tagalog or Taglish, respond naturally in the same language.

WHAT YOU NEVER DO:
- Never say "I'm here to listen and support you" as an opener more than once per conversation.
- Never repeat the same phrase twice in a conversation.
- Never say "as an AI" or break character.
- Never diagnose or prescribe anything.
- Never give a generic response that ignores what was just said.
- Never ask multiple questions at once.

HOW TO HANDLE DISTRESS LEVELS:
- No anxiety: Be natural and conversational. Gently explore what's on their mind.
- Low anxiety: Acknowledge the stress softly. Offer a simple grounding tip. Keep the conversation going.
- Moderate anxiety: Validate strongly. Offer a specific coping technique. Stay curious and warm.
- High anxiety: Be calm but urgent. Let them know help is on the way. Keep them talking and grounded.
- Crisis: Stay present. Provide crisis resources clearly. Never leave them alone in the conversation. Express genuine care.

CONTEXT AWARENESS:
- Always read the full conversation history before responding.
- Reference what the student said previously when relevant.
- If the student's mood is shifting (getting better or worse), acknowledge that shift naturally.
- If they mentioned something specific (a crush, an exam, a fear), remember it and bring it up naturally.

You are not a robot. You are GAIDA — and you genuinely care.
"""


def generate_response_with_gpt(
    user_message: str,
    session_context: Dict[str, Any] | None = None,
    anxiety_level: str | None = None,
    counselor_protocol: str | None = None,
) -> Dict[str, Any]:
    if not client:
        logger.error("OpenAI client is not initialized")
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
            context_note = level_tag
            if counselor_protocol:
                context_note += f"\n\nCounselor first aid protocol to follow:\n{counselor_protocol}"
            messages.append({"role": "system", "content": context_note})

    # Include last 10 messages from conversation history
    if session_context and isinstance(session_context.get("messages"), list) and len(session_context["messages"]) > 0:
        messages.append({
            "role": "system",
            "content": "The conversation history below is your memory. Reference it naturally — don't repeat what was already said, and build on what you know about this student."
        })
        # ← THIS PART IS MISSING — add it back
        for m in session_context["messages"][-10:]:
            role = "user" if m.get("sender") == "user" else "assistant"
            text = m.get("text", "")
            if text:
                messages.append({"role": role, "content": text})

    # Add current user message
    messages.append({"role": "user", "content": user_message})
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL_BASE,
            messages=messages,
            temperature=0.85,
            max_tokens=350,
        )

        content = None
        if hasattr(resp, "choices") and len(resp.choices) > 0:
            content = resp.choices[0].message.content

        if not content:
            logger.warning("GPT returned empty content")
            return {"response": None, "used": False}

        return {"response": content.strip(), "used": True}

    except Exception as e:
        logger.error("GPT call failed: %s", e)
        return {"response": None, "used": False}