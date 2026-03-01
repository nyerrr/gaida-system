import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_BASE = "gpt-3.5-turbo"
OPENAI_FINETUNED_MODEL = os.getenv("OPENAI_FINETUNED_MODEL", "ft:gpt-3.5-turbo-0125:personal::DEWms9GF")
