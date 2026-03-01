import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_BASE = "gpt-3.5-turbo"
OPENAI_FINETUNED_MODEL = os.getenv("OPENAI_FINETUNED_MODEL", "ft:gpt-3.5-turbo-0125:personal::DEWms9GF")
# External service timeouts (seconds)
OPENAI_TIMEOUT = float(os.getenv("OPENAI_TIMEOUT", "30"))
TTS_TIMEOUT = float(os.getenv("TTS_TIMEOUT", "15"))
STT_TIMEOUT = float(os.getenv("STT_TIMEOUT", "30"))

# Retry configuration
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_INITIAL_DELAY = float(os.getenv("RETRY_INITIAL_DELAY", "1"))  # seconds
RETRY_MAX_DELAY = float(os.getenv("RETRY_MAX_DELAY", "10"))  # seconds
RETRY_EXPONENTIAL_BASE = float(os.getenv("RETRY_EXPONENTIAL_BASE", "2"))