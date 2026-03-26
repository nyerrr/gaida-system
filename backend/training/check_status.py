import os

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

job = client.fine_tuning.jobs.retrieve("ftjob-04l6jiyEOZfB7BVsUwyzDQIu")

job = client.fine_tuning.jobs.retrieve("ftjob-04l6jiyEOZfB7BVsUwyzDQIu")
print("Status:", job.status)
print("Created at:", job.created_at)
print("Error:", job.error)  # check if something's wrong

print(job.status)