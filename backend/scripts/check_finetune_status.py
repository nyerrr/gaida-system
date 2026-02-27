# scripts/check_finetune_status.py
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load API key
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Replace this with your fine-tune job ID
job_id = "ftjob-NgTuEVpXskDJWp4mPFDM3Imu"

# Retrieve fine-tune job status
try:
    status = client.fine_tuning.jobs.retrieve(job_id)
    print("Fine-tune job status:", status.status)
    print("Fine-tuned model:", getattr(status, "fine_tuned_model", None))
    print("Error (if any):", getattr(status, "error", None))
   
except Exception as e:
    print("Error retrieving status:", e)