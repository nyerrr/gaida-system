"""Create a supervised fine-tuning job for GAIDA.

WARNING: OpenAI is winding down self-serve fine-tuning. New organisations were
blocked in 2026, and organisations that have not run inference on a fine-tuned
model in the last 60 days are blocked from creating new jobs. New job creation
ends for existing customers in January 2027. This script only works if your
organisation still has access; otherwise use the Fireworks managed path or the
retrieval/few-shot path described in QWEN3_TRAINING.md.

The previous version targeted `gpt-3.5-turbo`, which OpenAI shut down on
2026-10-23. This version targets `gpt-4.1-mini-2025-04-14` — a base that still
accepts the `temperature` + `max_tokens` call shape `gpt_agent.py` uses, so no
runtime code changes are needed.

Usage (from anywhere):

    python training/upload_file.py          # asks for confirmation first
    python training/upload_file.py --yes    # skip the confirmation prompt
    python training/upload_file.py --epochs 3 --yes   # cap training cost

Creating a job bills the account, so the confirmation exists on purpose.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

TRAINING_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TRAINING_DIR.parent
DATA_PATH = TRAINING_DIR / "finetune.jsonl"

DEFAULT_BASE_MODEL = "gpt-4.1-mini-2025-04-14"
DEFAULT_SUFFIX = "gaida-v2"

VALID_ROLES = {"system", "user", "assistant"}
MIN_EXAMPLES = 10

# Billing: training is charged per token, once per epoch.
# Source: https://developers.openai.com/api/docs/pricing (Fine-tuning, standard)
TRAINING_USD_PER_1M = 5.00  # gpt-4.1-mini-2025-04-14


def validate_dataset(path: Path) -> tuple[int, int, list[str]]:
    """Check the JSONL locally before uploading, so a bad line fails here
    instead of after the file has been billed and queued."""
    problems: list[str] = []
    examples = 0
    chars = 0

    with path.open(encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line:
                continue
            examples += 1
            chars += len(line)

            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                problems.append(f"line {lineno}: invalid JSON ({exc.msg})")
                continue

            messages = row.get("messages")
            if not isinstance(messages, list) or not messages:
                problems.append(f"line {lineno}: missing non-empty 'messages'")
                continue

            unknown = sorted(
                {m.get("role") for m in messages if m.get("role") not in VALID_ROLES}
            )
            if unknown:
                problems.append(f"line {lineno}: unknown role(s) {unknown}")
            if messages[-1].get("role") != "assistant":
                problems.append(f"line {lineno}: last message must be 'assistant'")
            if not any(
                m.get("role") == "assistant" and (m.get("content") or "").strip()
                for m in messages
            ):
                problems.append(f"line {lineno}: no assistant content")

    if examples < MIN_EXAMPLES:
        problems.append(
            f"only {examples} examples; OpenAI requires at least {MIN_EXAMPLES}"
        )

    return examples, chars, problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--yes", action="store_true", help="skip the confirmation prompt"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=None,
        metavar="N",
        help=(
            "cap the number of training epochs (billed per epoch). "
            "Omit to let OpenAI choose automatically."
        ),
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DATA_PATH,
        metavar="PATH",
        help=(
            "training JSONL to upload (default: training/finetune.jsonl). "
            "Use a merged file such as training/finetune_v2.jsonl to keep the "
            "original dataset untouched."
        ),
    )
    args = parser.parse_args()

    data_path = args.data
    if not data_path.is_absolute():
        data_path = (Path.cwd() / data_path).resolve()

    if args.epochs is not None and not 1 <= args.epochs <= 50:
        print("--epochs must be between 1 and 50.")
        return 1

    # Resolve the .env relative to the backend, not the shell's cwd.
    load_dotenv(dotenv_path=BACKEND_DIR / ".env")
    base_model = os.getenv("FINETUNE_BASE_MODEL", DEFAULT_BASE_MODEL)
    suffix = os.getenv("FINETUNE_SUFFIX", DEFAULT_SUFFIX)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is not set. Add it to backend/.env and retry.")
        return 1

    if not data_path.exists():
        print(f"Training file not found: {data_path}")
        return 1

    examples, chars, problems = validate_dataset(data_path)
    approx_tokens = chars // 4

    print(f"Training file : {data_path}")
    print(f"Examples      : {examples}")
    print(f"Approx tokens : ~{approx_tokens:,}")
    print(f"Base model    : {base_model}")

    epochs_label = str(args.epochs) if args.epochs else "auto"
    print(f"Epochs        : {epochs_label}")

    # Cost estimate. The token figure is a rough chars/4 approximation, and
    # training bills the full file once per epoch.
    if args.epochs:
        estimate = approx_tokens * args.epochs * TRAINING_USD_PER_1M / 1_000_000
        print(f"Est. training cost: ~${estimate:.2f} ({args.epochs} epochs)")
    else:
        low = approx_tokens * 2 * TRAINING_USD_PER_1M / 1_000_000
        high = approx_tokens * 10 * TRAINING_USD_PER_1M / 1_000_000
        print(f"Est. training cost: ~${low:.2f}–${high:.2f} (2–10 epochs, auto)")
        print("  Pass --epochs 3 to cap it at roughly "
              f"${approx_tokens * 3 * TRAINING_USD_PER_1M / 1_000_000:.2f}.")

    if problems:
        print("\nDataset validation FAILED:")
        for problem in problems[:20]:
            print(f"  - {problem}")
        if len(problems) > 20:
            print(f"  ... and {len(problems) - 20} more")
        return 1

    print("Dataset validation: OK")

    print(
        "\nWARNING: OpenAI is winding down self-serve fine-tuning. If this "
        "organisation has not run inference on a fine-tuned model in the last "
        "60 days, job creation will be rejected. Use the Fireworks managed "
        "path or retrieval/few-shot instead (see QWEN3_TRAINING.md)."
    )

    if not args.yes:
        answer = input("\nCreate the fine-tuning job now? This bills the account [y/N] ")
        if answer.strip().lower() not in {"y", "yes"}:
            print("Aborted — no file uploaded, no job created.")
            return 0

    client = OpenAI(api_key=api_key)

    print("\nUploading training file...")
    with data_path.open("rb") as training_file:
        uploaded = client.files.create(
            file=training_file,
            purpose="fine-tune",
        )
    print(f"File ID: {uploaded.id}")

    print("Creating fine-tuning job...")
    create_kwargs = {
        "training_file": uploaded.id,
        "model": base_model,
        "suffix": suffix,
    }
    if args.epochs:
        create_kwargs["hyperparameters"] = {"n_epochs": args.epochs}

    job = client.fine_tuning.jobs.create(**create_kwargs)

    print(f"\nJob ID : {job.id}")
    print(f"Status : {job.status}")
    print(f"Model  : {job.model}")
    print("\nPoll it with:")
    print(f"  python training/check_status.py {job.id}")
    print("\nDo NOT run this script again — each run starts a new billed job.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
