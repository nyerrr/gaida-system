from openai import OpenAI
from app.core.config import OPENAI_API_KEY, OPENAI_TIMEOUT

client = OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_TIMEOUT)