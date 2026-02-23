import json
from app.services.openai_client import client

SYSTEM_PROMPT = """
You are an intent classification system for a university mental health support chatbot.

Task:
Classify the emotional intent of the user's message.

Rules:
- Return ONLY valid JSON
- Do NOT explain
- Do NOT add extra text
- Do NOT give advice

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


def analyze_with_gpt(user_input: str):
    """
    Uses OpenAI to classify emotional intent.
    Returns:
    {
        "intent": str,
        "confidence": float
    }
    """

    # Fallback if API not available
    if not client:
        return {"intent": "other", "confidence": 0.5}

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",  # cheaper + fast
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input},
            ],
            temperature=0,
            max_tokens=60,
        )

        content = response.choices[0].message.content.strip()

        # Try parsing JSON safely
        result = json.loads(content)

        # Validate structure
        intent = result.get("intent", "other")
        confidence = float(result.get("confidence", 0.5))

        return {
            "intent": intent,
            "confidence": confidence
        }

    except Exception:
        return {
            "intent": "other",
            "confidence": 0.5
        }