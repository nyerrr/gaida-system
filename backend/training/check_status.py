"""Poll a GAIDA fine-tuning job, or list recent ones, or test a model.

Usage:

    python training/check_status.py                  # 10 most recent jobs
    python training/check_status.py ftjob-XXXX       # one job, with its model ID
    python training/check_status.py --ping ft:...    # does this model still answer?

OpenAI is winding down self-serve fine-tuning, but existing fine-tuned models
keep serving until their base model is retired. `--ping` is the fastest way to
find out whether the model from an earlier defense is still alive.

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
        print("\nTest that it still serves:")
        print(f"  python training/check_status.py --ping {job.fine_tuned_model}")
        print("\nThen use it in backend/.env (and the Render dashboard):")
        print(f"  LLM_MODEL={job.fine_tuned_model}")
    elif job.status == "succeeded":
        print("Model  : not assigned yet — re-run in a moment")
    else:
        print("Model  : not available until status is 'succeeded'")


def ping_model(client: OpenAI, model: str) -> int:
    """Send one tiny chat request to prove the model still serves.

    Returns 0 if the model answered, 1 otherwise. A failure here is the answer
    to the real question: the model from an earlier defense can no longer be
    used, so the defense must lean on the retrieval path.
    """
    print(f"Pinging {model} ...")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": "Reply with the single word: alive",
                }
            ],
            max_tokens=8,
            temperature=0,
        )
    except Exception as exc:  # noqa: BLE001 - we want the exact provider error
        detail = str(exc)
        print(f"\nFAILED: {type(exc).__name__}")
        print(detail)
        if "model_not_found" in detail or "does not exist" in detail:
            print(
                "\nThe model ID is not available to this account. Either the ID "
                "is wrong or OpenAI retired the base model.\n"
                "Treat it as dead: use the retrieval path, or train on Fireworks."
            )
        elif "deprecat" in detail.lower():
            print(
                "\nOpenAI retired this model. It will not serve again.\n"
                "Use the retrieval path, or train on Fireworks."
            )
        elif "permission" in detail.lower() or "organization" in detail.lower():
            print(
                "\nThis account cannot access that model. Confirm the key belongs "
                "to the organisation that created the fine-tune."
            )
        return 1

    reply = (response.choices[0].message.content or "").strip()
    print(f"\nALIVE. Reply: {reply!r}")
    print(f"Model returned: {response.model}")
    print("\nYou can use it in Render:")
    print(f"  LLM_MODEL={model}")
    print("  FINETUNE_FEWSHOT=0   # so the fine-tune's effect is clean")
    print("  # keep LLM_FALLBACK_* pointed at Groq")
    return 0


def main() -> int:
    load_dotenv(dotenv_path=BACKEND_DIR / ".env")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is not set. Add it to backend/.env and retry.")
        return 1

    client = OpenAI(api_key=api_key)

    args = sys.argv[1:]

    if args and args[0] == "--ping":
        if len(args) < 2:
            print("Usage: python training/check_status.py --ping <model-id>")
            print("Example: --ping ft:gpt-4.1-mini-2025-04-14:org:gaida:v1")
            return 1
        return ping_model(client, args[1])

    if args:
        job = client.fine_tuning.jobs.retrieve(args[0])
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
            print(
                f"       ping: python training/check_status.py --ping "
                f"{job.fine_tuned_model}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
