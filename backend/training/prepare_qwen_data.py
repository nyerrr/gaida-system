"""Validate and split GAIDA chat JSONL for Qwen3 SFT.

Usage: python backend/training/prepare_qwen_data.py
Writes train.jsonl and validation.jsonl beside the source file.
"""
import argparse
import json
import random
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(__file__).with_name("finetune.jsonl"))
    parser.add_argument("--validation-fraction", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "qwen_data")
    args = parser.parse_args()
    if not 0.05 <= args.validation_fraction <= 0.3:
        parser.error("validation-fraction must be between 0.05 and 0.3")

    rows = []
    with args.input.open(encoding="utf-8-sig") as src:
        for line_no, line in enumerate(src, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                parser.error(f"{args.input}:{line_no}: invalid JSON: {exc}")
            messages = row.get("messages")
            if not isinstance(messages, list) or not messages:
                parser.error(f"{args.input}:{line_no}: missing messages list")
            if any(not isinstance(m, dict) or m.get("role") not in {"system", "user", "assistant"}
                   or not isinstance(m.get("content"), str) for m in messages):
                parser.error(f"{args.input}:{line_no}: messages need valid role/content fields")
            if messages[-1]["role"] != "assistant":
                parser.error(f"{args.input}:{line_no}: last message must be assistant")
            rows.append({"messages": messages})

    if len(rows) < 20:
        parser.error(f"need at least 20 examples for a useful train/validation split; found {len(rows)}")
    random.Random(args.seed).shuffle(rows)
    n_val = max(1, round(len(rows) * args.validation_fraction))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, subset in (("validation.jsonl", rows[:n_val]), ("train.jsonl", rows[n_val:])):
        with (args.output_dir / name).open("w", encoding="utf-8") as out:
            for row in subset:
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Validated {len(rows)} examples; wrote {len(rows)-n_val} train and {n_val} validation rows to {args.output_dir}")
    print("Review the split for duplicate or near-duplicate conversations before training.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
