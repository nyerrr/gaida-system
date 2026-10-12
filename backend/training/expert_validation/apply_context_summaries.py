"""Attach plain-language conversation summaries to the Section A sheet.

The sampler (build_real_expert_sample.py) writes a verbatim `context` column
(earlier student messages, joined with " | "). That wording is hard for a
counsellor to read. This script merges an authored, paraphrased summary per
item from context_summaries.json into a `context_summary` column, which is
what the PDF prints.

Summaries are keyed by the normalized message text, so the sheet can be
re-numbered or refilled without losing them. Any item with no summary is
reported and the PDF falls back to the verbatim context.

    python apply_context_summaries.py
"""
import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV = HERE / "real_expert_sample.csv"
JSON = HERE / "context_summaries.json"


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def main() -> None:
    summaries = json.loads(JSON.read_text(encoding="utf-8"))
    with open(CSV, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
        fields = list(rows[0].keys())

    if "context_summary" not in fields:
        fields.append("context_summary")

    missing = []
    for r in rows:
        s = summaries.get(normalize(r["text"]), "")
        if not s:
            missing.append(r["sample_id"])
        r["context_summary"] = s

    with open(CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"rows            : {len(rows)}")
    print(f"with summary    : {len(rows) - len(missing)}")
    print(f"MISSING         : {', '.join(missing)}" if missing else
          "every item has a summary")


if __name__ == "__main__":
    main()
