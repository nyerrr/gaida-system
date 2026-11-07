"""Manual OpenAI connectivity check.

Run explicitly:  python test_gpt.py
This is NOT a pytest test — it makes a live API call. The main guard keeps
`pytest` collection from executing it (see pytest.ini too).

The old hardcoded `gpt-3.5-turbo` was retired and raised 404. Set OPENAI_MODEL
to test a specific model (e.g. the production fine-tune).
"""

import os

from dotenv import load_dotenv
from openai import OpenAI


def main() -> None:
    load_dotenv()

    key = os.getenv("OPENAI_API_KEY")
    print("Key found:", bool(key))
    print("Key preview:", key[:10] if key else "NONE")
    if not key:
        return

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    print("Model:", model)

    client = OpenAI(api_key=key)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Say hello"}],
        max_tokens=50,
    )
    print("Response:", resp.choices[0].message.content)


if __name__ == "__main__":
    main()
