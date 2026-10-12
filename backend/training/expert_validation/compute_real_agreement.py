"""
compute_real_agreement.py
-------------------------
Scores the real-data Section A expert sheet (real_expert_sample.csv):
percent agreement + Cohen's kappa between counselor A and counselor B on the
five-class blind labeling task.

This deliberately does NOT use gold_key.csv. The gold key belongs to the
synthetic detection evaluation (score_detection.py); the real packet has no
gold labels yet - its ground truth is the two counselors agreeing with each
other, optionally reconciled afterward by the team.

Usage (from backend/):
    python training/expert_validation/compute_real_agreement.py
    # after counselors fill counselor_A_label + counselor_B_label columns

Labels accepted (case-insensitive): anxiety, sadness, neutral, suicidal, anger,
plus loss (counted under sadness when scoring, mirroring compute_agreement.py).
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

try:
    from sklearn.metrics import cohen_kappa_score
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

BASE = Path(__file__).resolve().parent
SAMPLE = BASE / "real_expert_sample.csv"

CANON = {
    "anxiety": "anxiety",
    "anxious": "anxiety",
    "sadness": "sadness",
    "sad": "sadness",
    "grief": "sadness",
    "depression": "sadness",
    "depressed": "sadness",
    "loss": "sadness",
    "neutral": "neutral",
    "suicidal": "suicidal",
    "suicide": "suicidal",
    "anger": "anger",
    "angry": "anger",
}


def canon(label: str):
    return CANON.get((label or "").strip().lower())


def main() -> None:
    with open(SAMPLE, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    pairs = []
    missing = 0
    for r in rows:
        a = canon(r.get("counselor_A_label"))
        b = canon(r.get("counselor_B_label"))
        if not a or not b:
            missing += 1
        else:
            pairs.append((r["sample_id"], a, b))

    if not pairs:
        print(f"No complete A/B label pairs yet ({missing} rows with blanks).")
        print("Fill counselor_A_label and counselor_B_label in "
              f"{SAMPLE.name}, then re-run.")
        sys.exit(0)

    agree = sum(1 for _, a, b in pairs if a == b)
    pct = 100.0 * agree / len(pairs)
    print(f"Rows scored: {len(pairs)}  (skipped blank/incomplete: {missing})")
    print(f"Exact agreement: {agree}/{len(pairs)} = {pct:.1f}%")

    if HAS_SKLEARN:
        kappa = cohen_kappa_score([a for _, a, _ in pairs],
                                  [b for _, _, b in pairs])
        print(f"Cohen's kappa   : {kappa:.3f}")

    print("\nPer-class agreement (A vs B):")
    by_a: dict[str, tuple[int, int]] = {}
    for _, a, b in pairs:
        tot, ok = by_a.get(a, (0, 0))
        by_a[a] = (tot + 1, ok + (1 if a == b else 0))
    for cls, (tot, ok) in sorted(by_a.items()):
        print(f"  {cls:9s} {ok:3d}/{tot:3d} agree  ({100.0 * ok / tot:.0f}%)")

    dis = Counter((a, b) for _, a, b in pairs if a != b)
    if dis:
        print("\nMost common disagreements (A -> B):")
        for (a, b), n in dis.most_common(6):
            print(f"  {a:9s} -> {b:9s} ({n})")


if __name__ == "__main__":
    main()