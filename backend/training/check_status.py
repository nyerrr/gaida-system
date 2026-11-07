"""Poll a GAIDA fine-tuning job, or list recent ones.

Usage:

    python training/check_status.py             # 10 most recent jobs
    python training/check_status.py ftjob-XXXX  # one job, with its model ID

The previous version had a hardcoded job ID for the retired gpt-3.5-turbo job.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

BACKEND_DIR = Path(__file__).resolve().parent.parent


def summarize(job) -> None:
    print(f"Job ID : {job.id}")
    print(f"Status : {job.status}")
    print(f"Base   : {job.model}")
    print(f"Trained: {job.trained_tokens if job.trained_tokens else 'n/a'} tokens")

    if job.error:
        print(f"Error  : {job.error}")

    # `fine_tuned_model` stays None until the job reaches "succeeded".
    if job.fine_tuned_model:
        print(f"Model  : {job.fine_tuned_model}")
        print("\nUse it in backend/.env (and the Render dashboard):")
        print(f"  OPENAI_MODEL={job.fine_tuned_model}")
    elif job.status == "succeeded":
        print("Model  : not assigned yet — re-run in a moment")
    else:
        print("Model  : not available until status is 'succeeded'")


def main() -> int:
    load_dotenv(dotenv_path=BACKEND_DIR / ".env")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is not set. Add it to backend/.env and retry.")
        return 1

    client = OpenAI(api_key=api_key)

    if len(sys.argv) > 1:
        job = client.fine_tuning.jobs.retrieve(sys.argv[1])
        summarize(job)
        return 0

    print("No job ID given — showing the 10 most recent jobs.\n")
    jobs = list(client.fine_tuning.jobs.list(limit=10).data)
    if not jobs:
        print("No fine-tuning jobs found on this account.")
        return 0

    for job in jobs:
        created = datetime.fromtimestamp(job.created_at, tz=timezone.utc)
        print(
            f"{job.id}  {job.status:<12}  {job.model}  "
            f"(created {created:%Y-%m-%d %H:%M UTC})"
        )
        if job.fine_tuned_model:
            print(f"    -> {job.fine_tuned_model}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
