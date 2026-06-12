import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

key = os.getenv("OPENAI_API_KEY")
print("Key found:", bool(key))
print("Key preview:", key[:10] if key else "NONE")

client = OpenAI(api_key=key)

resp = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Say hello"}],
    max_tokens=50,
)

print("Response:", resp.choices[0].message.content)