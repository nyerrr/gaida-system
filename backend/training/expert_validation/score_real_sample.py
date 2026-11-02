"""
score_real_sample.py
--------------------
Compares GAIDA's detector with the four counselors who labeled the 100 real
pilot messages in "GAIDA - Expert Validation (Section A)".

INPUT   expert_labels_real.csv  (item_id, text, evaluator_1..evaluator_4;
        evaluators are anonymized, in the order the responses arrived)
OUTPUT  a printed report + real_detection_results.csv (every item with GAIDA's
        label, each counselor's label, and the majority)

WHAT IT MEASURES
    * GAIDA vs the counselors' majority label (only items where at least 3 of
      the 4 counselors agree - the others have no reliable "right answer")
    * GAIDA vs each counselor (Cohen's kappa), next to the counselor-vs-counselor
      kappa, so GAIDA is judged against how much professionals agree with each
      other, not against a perfect score
    * SAFETY: every message that any counselor marked "suicidal", and what GAIDA
      did with it

LIMITATION (state this in the thesis): GAIDA sees each message on its own, in a
fresh session. The counselors also saw a short summary of the earlier chat.

Nothing is written to the database (dry-run mode is switched on below).

USAGE
    cd backend
    python training/expert_validation/score_real_sample.py
"""

import csv
import itertools
import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("GAIDA_DISABLE_PERSISTENCE", "1")

BASE = Path(__file__).resolve().parent
BACKEND = BASE.parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

CLASSES = ["anxiety", "sadness", "neutral", "suicidal", "anger"]
EVALUATORS = ["evaluator_1", "evaluator_2", "evaluator_3", "evaluator_4"]

# GAIDA can return intents the counselors' five-way scheme does not have.
# "stress" is counted as anxiety (the counselors themselves said the two overlap).
GAIDA_TO_SCHEME = {
    "anxiety": "anxiety", "stress": "anxiety",
    "sadness": "sadness", "grief": "sadness", "loss": "sadness",
    "neutral": "neutral",
    "suicidal": "suicidal", "crisis": "suicidal",
    "anger": "anger",
}


def kappa(a, b):
    """Cohen's kappa for two equal-length label lists."""
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in set(ca) | set(cb))
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def load_rows():
    with open(BASE / "expert_labels_real.csv", "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def majority(row):
    """The label at least 3 of 4 counselors chose, else None."""
    label, n = Counter(row[e] for e in EVALUATORS).most_common(1)[0]
    return label if n >= 3 else None


def analyze(rows, preds):
    """rows: csv rows; preds: list of dicts {label, level, severity, raw}."""
    out = []
    for row, p in zip(rows, preds):
        out.append({**row, "gaida": p["label"], "gaida_raw": p["raw"],
                    "level": p["level"], "severity": p["severity"],
                    "majority": majority(row) or ""})
    return out


def report(res):
    n = len(res)
    print("=" * 70)
    print("GAIDA vs the four counselors - 100 real pilot messages")
    print("=" * 70)

    # Safety first.
    flagged = [r for r in res if any(r[e] == "suicidal" for e in EVALUATORS)]
    print(f"\nSAFETY: messages any counselor marked 'suicidal': {len(flagged)}")
    for r in flagged:
        votes = Counter(r[e] for e in EVALUATORS)
        print(f"  {r['item_id']}  GAIDA={r['gaida_raw']:<9} level={r['level']:<9} "
              f"severity={r['severity']:<9} counselors={dict(votes)}")
        print(f"      {r['text'][:90]}")

    # Against the majority.
    scored = [r for r in res if r["majority"]]
    hit = sum(1 for r in scored if r["gaida"] == r["majority"])
    print(f"\nGAIDA vs majority label (items where >=3 of 4 counselors agree): "
          f"{hit}/{len(scored)} = {100 * hit / max(len(scored), 1):.1f}%")
    print(f"  ({n - len(scored)} items had no majority and are excluded)")
    k = kappa([r["gaida"] for r in scored], [r["majority"] for r in scored])
    print(f"  Cohen's kappa vs majority: {k:.3f}")

    print("\nPer class (counselor majority = truth)")
    print(f"  {'class':<10}{'n':>4}{'GAIDA recall':>14}   most common mistake")
    for c in CLASSES:
        sub = [r for r in scored if r["majority"] == c]
        if not sub:
            continue
        ok = sum(1 for r in sub if r["gaida"] == c)
        wrong = Counter(r["gaida"] for r in sub if r["gaida"] != c)
        m = wrong.most_common(1)
        print(f"  {c:<10}{len(sub):>4}{100 * ok / len(sub):>13.0f}%   "
              f"{('read as ' + m[0][0] + ' (' + str(m[0][1]) + ')') if m else '-'}")

    print("\nConfusion matrix (rows = counselor majority, cols = GAIDA)")
    print(f"  {'':<10}" + "".join(f"{c[:6]:>8}" for c in CLASSES))
    for t in CLASSES:
        print(f"  {t:<10}" + "".join(
            f"{sum(1 for r in scored if r['majority'] == t and r['gaida'] == p):>8}"
            for p in CLASSES))

    # GAIDA as a fifth evaluator.
    print("\nKappa: GAIDA vs each counselor (all 100 items)")
    g = [r["gaida"] for r in res]
    gk = []
    for e in EVALUATORS:
        kk = kappa(g, [r[e] for r in res]); gk.append(kk)
        ag = sum(1 for r in res if r["gaida"] == r[e])
        print(f"  GAIDA vs {e}: agreement {ag}%  kappa {kk:.3f}")
    ck = [kappa([r[a] for r in res], [r[b] for r in res])
          for a, b in itertools.combinations(EVALUATORS, 2)]
    print(f"\n  average GAIDA-vs-counselor kappa : {sum(gk) / len(gk):.3f}")
    print(f"  average counselor-vs-counselor   : {sum(ck) / len(ck):.3f}")
    print("  (if the first is close to the second, GAIDA disagrees with a "
          "counselor about as often as counselors disagree with each other)")


def run_detector(rows):
    from app.services.intent_router import _prepare_turn
    from app.services.session_manager import SESSIONS

    preds = []
    for row in rows:
        sid = f"realsample-{row['item_id']}"
        SESSIONS[sid] = {
            "session_id": sid, "user_id": None,
            "started_at": "1970-01-01T00:00:00Z", "messages": [], "active": True,
            "meta": {"running_confidence": 0.3, "running_intent": "neutral",
                     "peak_severity": "Normal", "peak_confidence": 0.3},
        }
        turn = _prepare_turn(row["text"], session_id=sid)
        raw = (turn.get("intent") or "neutral").strip().lower()
        preds.append({
            "label": GAIDA_TO_SCHEME.get(raw, "neutral"),
            "raw": raw,
            "level": turn.get("anxiety_level") or "none",
            "severity": turn.get("severity") or "-",
        })
    return preds


def main():
    rows = load_rows()
    res = analyze(rows, run_detector(rows))
    report(res)
    path = BASE / "real_detection_results.csv"
    cols = ["item_id", "text", *EVALUATORS, "majority", "gaida", "gaida_raw",
            "level", "severity"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in res:
            w.writerow({c: r.get(c, "") for c in cols})
    print(f"\nWrote {path.name}")


if __name__ == "__main__":
    main()
