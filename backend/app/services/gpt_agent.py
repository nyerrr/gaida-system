import os
import json
from dotenv import load_dotenv
from typing import Dict, Any
from app.core.config import OPENAI_MODEL_BASE

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

load_dotenv()

_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = None
if OpenAI and _OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=_OPENAI_API_KEY)
    except Exception:
        client = None


SYSTEM_PROMPT = """
You are an empathetic, supportive virtual agent for mental health guidance. Follow these rules:
- Always respond in a calm, non-judgmental, concise, and empathetic manner.
- Provide grounding suggestions and short coping strategies, not diagnoses.
- If the user indicates self-harm or suicidal intent, include an escalation flag but do NOT provide instructions for self-harm.
- Keep responses brief (1-3 sentences) unless the user asks for more.
Return only the plain assistant message as text in the assistant role (no extra JSON).
"""


def generate_response_with_gpt(user_message: str, session_context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Generates an empathetic response using the OpenAI client if available.

    Returns: {"response": str, "used": bool}
    """
    if not client:
        return {"response": None, "used": False}

    # Build messages: system prompt, then recent session messages if available
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if session_context and isinstance(session_context.get("messages"), list):
        # include last up to 10 messages as context
        for m in session_context["messages"][-10:]:
            role = "user" if m.get("sender") == "user" else "assistant"
            text = m.get("text", "")
            messages.append({"role": role, "content": text})

    # add current user input
    messages.append({"role": "user", "content": user_message})

    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL_BASE,
            messages=messages,
            temperature=0.7,
            max_tokens=200,
        )

        content = None
        if hasattr(resp, "choices") and len(resp.choices) > 0:
            choice = resp.choices[0]
            if hasattr(choice, "message") and choice.message is not None:
                content = getattr(choice.message, "content", None) or choice.message.get("content")
            else:
                content = getattr(choice, "text", None)

        if not content:
            return {"response": None, "used": False}

        return {"response": content.strip(), "used": True}

    except Exception:
        return {"response": None, "used": False}
