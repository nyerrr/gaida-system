import json
from app.services.openai_client import client
from backend.app.core.config import OPENAI_MODEL_BASE

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


def analyze_with_gpt(user_input: str):

    if not client:
        return {"intent": "other", "confidence": 0.5}

    try:
        response = client.chat.completions.create(
            model="ft:gpt-3.5-turbo-0125:personal::DDu4xxxR",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input},
            ],
            temperature=0,
            response_format={"type": "json_object"},  # important
            max_tokens=50,
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        return {
            "intent": result.get("intent", "other"),
            "confidence": float(result.get("confidence", 0.5)),
        }

    except Exception as e:
        print("Intent detection error:", e)
        return {
            "intent": "other",
            "confidence": 0.5
        }