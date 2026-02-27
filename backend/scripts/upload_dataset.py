# scripts/upload_dataset.py
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load API key from .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Path to your JSONL training file
file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "training", "anxiety_training.jsonl")

# Upload the dataset
try:
    uploaded_file = client.files.create(
        file=open(file_path, "rb"),
        purpose="fine-tune"
    )
    print("File uploaded successfully! File ID:", uploaded_file.id)
except FileNotFoundError:
    print("File not found. Make sure 'anxiety_training.jsonl' is in backend/training/")
except Exception as e:
    print("Error uploading file:", e)