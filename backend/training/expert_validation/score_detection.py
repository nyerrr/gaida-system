"""
score_detection.py
------------------
Runs GAIDA's detection pipeline against gold_key.csv and reports what it got
right.

WHY THIS EXISTS
    Every claim that GAIDA "understands students better" was made by reading
    individual replies. A reply that names the contradiction well tells you
    nothing about whether GAIDA correctly recognised the situation that
    produced it — those are two different failures. gold_key.csv already holds
    120 labelled messages, but it was only ever used to score COUNSELLORS
    against each other (compute_agreement.py). GAIDA itself was never
    measured. So detection had no number at all, and no way to tell a prompt
    fix from a regression.

WHAT IT DOES
    Calls the real pipeline entry point (_prepare_turn — steps 1-6 of a chat
    turn: detection, confidence running, severity mapping) once per gold
    message, each in a fresh session, and compares the resulting intent to the
    gold label.

    It stops before the GPT reply on purpose. Detection is what we are
    measuring; generating a reply costs 10x more and cannot change the number.

    Nothing is written to the database. Each message gets a pre-seeded
    in-memory session so start_session() returns early instead of inserting a
    throwaway row into Supabase per message.

THE NUMBER THAT MATTERS MOST
    A gold `suicidal` message that is not routed to crisis is a different kind
    of wrong from a gold `neutral` message misread as `anxiety`. The first
    means a student in danger did not get the crisis flow and no counselor was
    alerted. Those are listed on their own, before the confusion matrix, so
    they cannot be averaged away into an accuracy figure.

USAGE
    cd backend
    .\\venv\\Scripts\\python.exe training/expert_validation/score_detection.py
    .\\venv\\Scripts\\python.exe training/expert_validation/score_detection.py --limit 20
"""

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
BACKEND = BASE.parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.intent_router import _prepare_turn  # noqa: E402
from app.services.session_manager import SESSIONS  # noqa: E402
from compute_agreement import _norm  # noqa: E402

CLASSES = ["suicidal", "anger", "anxiety", "sadness", "neutral"]


def load_gold():
    with open(BASE / "gold_key.csv", "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _blank_session(sid):
    """A throwaway session that is already in memory.

    start_session() checks this dict first and returns immediately, which is
    what keeps 120 evaluation turns out of the production session store.
    """
    SESSIONS[sid] = {
        "session_id": sid,
        "user_id": None,
        "started_at": "1970-01-01T00:00:00Z",
        "messages": [],
        "active": True,
        "meta": {
            "running_confidence": 0.3,
            "running_intent": "neutral",
            "peak_severity": "Normal",
            "peak_confidence": 0.3,
        },
    }
    return sid


def is_filipino(text):
    """Rough Tagalog/Taglish check, for the per-language breakdown only."""
    from app.services.gpt_agent import _uses_filipino

    return _uses_filipino(text)


def run(rows):
    results = []
    for row in rows:
        sid = _blank_session(f"goldkey-{row['sample_id']}")
        turn = _prepare_turn(row["text"], session_id=sid)
        confidence = turn.get("running_confidence")
        results.append(
            {
                "sample_id": row["sample_id"],
                "text": row["text"],
                "gold": _norm(row["gold_label"]),
                # Not every intent maps to a response flow, so intent can come
                # back unnamed and level can be absent. Kept verbatim rather
                # than defaulted — "no level" is itself a finding.
                "predicted": _norm(turn.get("intent")) or "unknown",
                "level": turn.get("anxiety_level") or "none",
                "severity": turn.get("severity") or "-",
                "confidence": float(confidence) if confidence is not None else 0.0,
                "language": "filipino" if is_filipino(row["text"]) else "english",
            }
        )
    return results


def report(results):
    n = len(results)
    correct = sum(1 for r in results if r["gold"] == r["predicted"])

    # ── Safety-critical first, so it is the first thing on screen ──────────
    missed_crisis = [
        r for r in results if r["gold"] == "suicidal" and r["level"] != "crisis"
    ]
    crisis_total = sum(1 for r in results if r["gold"] == "suicidal")
    print("=" * 68)
    print("SAFETY-CRITICAL: gold 'suicidal' not routed to crisis flow")
    print("=" * 68)
    if missed_crisis:
        for r in missed_crisis:
            print(
                f"  #{r['sample_id']:<4} -> {r['predicted']:<9} "
                f"level={r['level']:<9} conf={r['confidence']:.2f}  {r['text'][:58]}"
            )
        print(f"\n  {len(missed_crisis)}/{crisis_total} suicidal messages missed.")
    else:
        print(f"  none — all {crisis_total} suicidal messages reached the crisis flow.")

    # ── Overall ───────────────────────────────────────────────────────────
    print()
    print(f"Overall accuracy: {correct}/{n} = {correct / max(n, 1) * 100:.1f}%")

    # ── Per class ─────────────────────────────────────────────────────────
    print()
    print("Per class (recall = how many of that class GAIDA recognised)")
    print(f"  {'class':<10} {'n':>3} {'recall':>8}   {'most common mistake'}")
    for cls in CLASSES:
        subset = [r for r in results if r["gold"] == cls]
        if not subset:
            continue
        hit = sum(1 for r in subset if r["predicted"] == cls)
        wrong = Counter(r["predicted"] for r in subset if r["predicted"] != cls)
        mistake = wrong.most_common(1)[0] if wrong else None
        note = f"read as {mistake[0]} ({mistake[1]})" if mistake else "-"
        print(f"  {cls:<10} {len(subset):>3} {hit / len(subset) * 100:>7.1f}%   {note}")

    # ── Confusion matrix ──────────────────────────────────────────────────
    print()
    print("Confusion matrix (rows = gold, cols = predicted)")
    header = "".join(f"{c[:6]:>8}" for c in CLASSES)
    print(f"  {'gold':<10}{header}")
    for gold_cls in CLASSES:
        row = [r for r in results if r["gold"] == gold_cls]
        cells = ""
        for pred_cls in CLASSES:
            mark = str(sum(1 for r in row if r["predicted"] == pred_cls))
            cells += f"{mark:>8}"
        print(f"  {gold_cls:<10}{cells}")

    # ── Language split ───────────────────────────────────────────────────
    print()
    print("By language (is there a Filipino gap?)")
    for lang in ("english", "filipino"):
        subset = [r for r in results if r["language"] == lang]
        if not subset:
            continue
        hit = sum(1 for r in subset if r["gold"] == r["predicted"])
        print(f"  {lang:<10} {hit}/{len(subset)} = {hit / len(subset) * 100:.1f}%")


def write_misses(results):
    path = BASE / "detection_misses.csv"
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "sample_id", "gold", "predicted", "level", "severity",
                "confidence", "language", "text",
            ],
        )
        w.writeheader()
        for r in results:
            if r["gold"] != r["predicted"]:
                w.writerow(r)
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="score only the first N")
    args = ap.parse_args()

    rows = load_gold()
    if args.limit:
        rows = rows[: args.limit]

    results = run(rows)
    report(results)
    misses = write_misses(results)
    print(f"\nMisses written to {misses}")