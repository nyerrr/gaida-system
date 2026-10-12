"""
build_training_audit.py
-----------------------
Builds Section B, the training-label audit sheet.

It selects a HAND-CURATED set of the clearest exemplars for each of the five
labels (18 per class, 90 total) from the real training data
(anxiety_training.jsonl). A mental-health professional then confirms or corrects
our label for each row, which verifies the dataset the classifier learned from.

Why curated, not random: the sheet is a label-integrity check, so it should
contain unambiguous cases of each category. The sample is balanced (18 per
class, 20% each) on purpose - it is NOT the training distribution, and must not
be read as one.

Outputs:
  * training_audit.csv       -- sent to counselors (sample_id, text, current_label, counselor_verdict)
  * training_audit_form.html -- printable version
"""

import csv
import html
import json
import random
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE.parent / "anxiety_training.jsonl"

PER_CLASS = 18
SHUFFLE_SEED = 7          # fixed so the sheet order is reproducible
MIN_LEN, MAX_LEN = 12, 240

# 1-based positions into the filtered, de-duplicated candidate list per label
# (see _candidates()). Each index is a clear, self-contained example of its
# label. Anything mislabeled, duplicated, bot-directed, or ambiguous is left out.
SELECTION = {
    "anxiety": [8, 14, 21, 24, 32, 51, 53, 56, 57, 60, 70, 91,
                105, 106, 110, 123, 130, 143],
    "sadness": [2, 23, 24, 26, 33, 36, 57, 61, 63, 69, 77, 80,
                84, 95, 97, 100, 25, 28],
    "neutral": [3, 4, 10, 12, 13, 14, 15, 17, 27, 28, 29, 30,
                37, 40, 46, 50, 60, 63],
    "suicidal": [1, 3, 4, 7, 10, 13, 20, 25, 27, 30, 33, 35,
                 37, 38, 44, 48, 49, 90],
    "anger": [2, 3, 6, 9, 11, 12, 13, 21, 24, 26, 28, 31,
              33, 37, 41, 42, 44, 45],
}


def load_rows():
    rows = []
    with open(DATA, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _candidates(rows):
    """De-duplicated, length-filtered text lists per label (order preserved)."""
    by_label = {}
    seen = {}
    for r in rows:
        text = re.sub(r"\s+", " ", r["text"].strip())
        if len(text) < MIN_LEN or len(text) > MAX_LEN:
            continue
        label = r["label"]
        key = text.lower()
        if key in seen.get(label, set()):
            continue
        seen.setdefault(label, set()).add(key)
        by_label.setdefault(label, []).append({"text": text, "label": label})
    return by_label


def _curated():
    by_label = _candidates(load_rows())
    picked = []
    for label, idxs in SELECTION.items():
        pool = by_label.get(label, [])
        if len(idxs) != PER_CLASS:
            raise SystemExit(f"{label}: expected {PER_CLASS} indices, got {len(idxs)}")
        if max(idxs) > len(pool):
            raise SystemExit(f"{label}: index out of range (pool {len(pool)})")
        picked += [pool[i - 1] for i in idxs]
    random.Random(SHUFFLE_SEED).shuffle(picked)
    return picked


def _write_csv(picked):
    with open(BASE / "training_audit.csv", "w", encoding="utf-8-sig",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["sample_id", "text", "current_label", "counselor_verdict"])
        for i, r in enumerate(picked, start=1):
            w.writerow([i, r["text"], r["label"], ""])


def _write_form(picked):
    rows_html = "".join(
        "<tr><td class=\"num\">{num}</td><td>{msg}</td>"
        "<td class=\"cur\">{cur}</td><td class=\"opt\"></td>"
        "<td class=\"fix\"></td></tr>".format(
            num=i, msg=html.escape(r["text"]), cur=r["label"]
        )
        for i, r in enumerate(picked, start=1)
    )

    doc = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>GAIDA - Training Data Label Audit</title>
<style>
  body {{ margin: 10mm; font-family: Arial, sans-serif; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 11px; }}
  th, td {{ border: 1px solid #bbb; padding: 4px 6px; vertical-align: middle; }}
  th {{ background: #eee; font-weight: bold; text-align: left; }}
  tr {{ page-break-inside: avoid; }}
  .num {{ width: 30px; text-align: center; }}
  .msg {{ width: 46%; }}
  .cur {{ width: 12%; text-align: center; font-weight: bold; }}
  .opt {{ width: 14%; text-align: center; }}
  .fix {{ width: 22%; }}
  .sig {{ margin-top: 28px; font-size: 12px; }}
  .sig td {{ border: none; padding: 10px 0; }}
  @media print {{
    body {{ margin: 10mm; }}
    thead {{ display: table-header-group; }}
  }}
</style>
</head>
<body>

<h1>GAIDA - Training Data Label Audit</h1>
<p class="muted">AI-based Anxiety Detection System &middot; College Guidance &middot; University of the East</p>

<p><b>Purpose.</b> GAIDA's model is trained on student-like messages that our team labeled across
5 categories. We ask a licensed mental health professional to AUDIT the correctness of these labels:
for each message, our current label is shown. Please check <b>Agree</b> if the label is correct, or
write the corrected label in the last column if it is not.</p>

<p class="muted">This is a balanced audit sample (18 per class, 20% each); it is not the training
distribution.</p>

<p><b>Time required:</b> approximately 10&ndash;15 minutes.</p>

<h2>Label Definitions (with examples)</h2>
<ul>
  <li><b>anxiety</b> - nervousness, worry, tension, dread, panic-like feelings, overthinking</li>
  <li><b>sadness</b> - low mood, grief, loneliness, emptiness, crying</li>
  <li><b>neutral</b> - casual or everyday statements with no significant distress</li>
  <li><b>suicidal</b> - death wishes, wanting to end one's life, self-harm - even when phrased indirectly</li>
  <li><b>anger</b> - irritation, frustration, hostility</li>
</ul>

<table>
  <thead>
  <tr><th class="num">#</th><th class="msg">Student Message</th>
  <th class="cur">Current Label</th><th class="opt">Agree (check)</th>
  <th class="fix">If NOT agree, corrected label:</th></tr>
  </thead>
  <tbody>
{rows_html}
  </tbody>
</table>

<table class="sig">
  <tr>
    <td><b>Counselor name:</b> ______________________________</td>
    <td><b>Date:</b> ___________________</td>
  </tr>
  <tr>
    <td><b>Signature:</b> ___________________________________</td>
    <td><b>List name (A or B):</b> ________</td>
  </tr>
</table>

</body>
</html>
""".format(rows_html=rows_html)

    with open(BASE / "training_audit_form.html", "w", encoding="utf-8") as f:
        f.write(doc)


def main():
    picked = _curated()
    dist = {}
    for r in picked:
        dist[r["label"]] = dist.get(r["label"], 0) + 1
    print("Sample:", dist, "| total:", len(picked))
    for r in picked:
        print(f"  [{r['label']:8}] {r['text']}")
    _write_csv(picked)
    _write_form(picked)
    print("Wrote training_audit.csv and training_audit_form.html")


if __name__ == "__main__":
    main()
