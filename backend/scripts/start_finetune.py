# scripts/start_finetune.py
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load API key from .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Path to your training file
file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "training", "anxiety_training.jsonl")

# Upload the file (optional: skip if already uploaded)
try:
    uploaded_file = client.files.create(
        file=open(file_path, "rb"),
        purpose="fine-tune"
    )
    file_id = uploaded_file.id
    print("File uploaded successfully! File ID:", file_id)
except Exception as e:
    print("Error uploading file:", e)
    exit(1)

# Start fine-tuning GPT-3.5-turbo
try:
    job = client.fine_tuning.jobs.create(
        training_file="file-8YVKRzaFW5tCzQ2biDqcGf",
        model="gpt-3.5-turbo"
    )
    print("Fine-tune job started! Job ID:", job.id)
except Exception as e:
    print("Error starting fine-tune job:", e)