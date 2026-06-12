import os

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# STEP 1: Upload training file
file = client.files.create(
    file=open("training/finetune.jsonl", "rb"),
    purpose="fine-tune"
)

print("File ID:", file.id)


# STEP 2: Create fine-tuning job
job = client.fine_tuning.jobs.create(
    training_file=file.id,
    model="gpt-3.5-turbo"
)

print("Job ID:", job.id)


# STEP 3: Check job status
status = client.fine_tuning.jobs.retrieve(job.id)
print("Status:", status.status)