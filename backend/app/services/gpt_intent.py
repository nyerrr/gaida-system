import os
import os
import json
from dotenv import load_dotenv

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

load_dotenv()

# Create client only when OpenAI SDK is available and API key is set.
_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = None
if OpenAI and _OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=_OPENAI_API_KEY)
    except Exception:
        client = None

SYSTEM_PROMPT = """
You are an intent classification system for a mental health support application.

Rules:
- Classify emotional intent ONLY.
- Do NOT give advice.
- Do NOT generate supportive messages.
- Do NOT add explanations.

Allowed intent labels:
- anxiety
- sadness
- stress
- neutral
- other

Output STRICT JSON only:
{
  "intent": "<label>",
  "confidence": <number between 0 and 1>
}
"""


def analyze_with_gpt(user_input: str):
    """Call OpenAI to classify intent. If OpenAI isn't configured, return a conservative fallback.

    Returns a dict: {"intent": <label>, "confidence": <float>}
    """
    if not client:
        return {"intent": "other", "confidence": 0.5}

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input},
            ],
            temperature=0.0,
        )

        content = None
        if hasattr(response, "choices") and len(response.choices) > 0:
            choice = response.choices[0]
            if hasattr(choice, "message") and choice.message is not None:
                content = getattr(choice.message, "content", None) or choice.message.get("content")
            else:
                content = getattr(choice, "text", None)

        if not content:
            raise ValueError("no content in completion")

        return json.loads(content)

    except Exception:
        return {"intent": "other", "confidence": 0.5}
