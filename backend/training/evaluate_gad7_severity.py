"""Grouped cross-validation for text prediction of existing GAD-7 bands.

This is an offline research experiment. It does not alter GAIDA's production
classifier or save model artifacts. It uses one aggregated text record per
session and keeps known students in a single fold.

Run from backend/:
    .\\venv\\Scripts\\python.exe training/evaluate_gad7_severity.py

The default input is the existing research_export_for_review.csv. Only the
gad7_band column is used as the target; candidate_label is intentionally
ignored because that export maps GAD-7 bands to intent categories.
"""

from __future__ import annotations

import csv
import json
import sys
import warnings
from collections import Counter, defaultdict
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.text_prep import STOPWORDS, preprocess

warnings.filterwarnings("ignore", category=UserWarning)

INPUT = BACKEND / "research_export_for_review.csv"
OUTPUT = BACKEND / "training" / "pilot_analysis" / "gad7_severity_cv_report.json"
CLASSES = ["minimal", "mild", "moderate", "severe"]


def load_session_documents() -> tuple[list[str], list[str], list[str]]:
    by_session: dict[str, dict] = {}
    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            sid = (row.get("session_id") or "").strip()
            text = (row.get("text") or "").strip()
            label = (row.get("gad7_band") or "").strip().lower()
            if not sid or not text or label not in CLASSES:
                continue
            item = by_session.setdefault(
                sid,
                {
                    "parts": [],
                    "label": label,
                    "student_id": (row.get("student_id") or "").strip(),
                },
            )
            if item["label"] != label:
                raise ValueError(f"Conflicting GAD-7 bands within session {sid}")
            item["parts"].append(text)
            if not item["student_id"]:
                item["student_id"] = (row.get("student_id") or "").strip()

    texts, labels, groups = [], [], []
    for sid, item in by_session.items():
        # Identified sessions from one student stay in the same fold. Anonymous
        # sessions have no stable participant ID in the export, so session ID
        # is the safest available grouping key for them.
        group = item["student_id"] or f"anonymous-session:{sid}"
        texts.append(" ".join(item["parts"]))
        labels.append(item["label"])
        groups.append(group)
    return texts, labels, groups


def make_models() -> dict[str, Pipeline]:
    vectorizer = {
        "ngram_range": (1, 2),
        "max_features": 5000,
        "sublinear_tf": True,
        "preprocessor": preprocess,
        "stop_words": sorted(STOPWORDS),
    }
    return {
        "Logistic Regression": Pipeline([
            ("tfidf", TfidfVectorizer(**vectorizer)),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
        ]),
        "Random Forest": Pipeline([
            ("tfidf", TfidfVectorizer(**vectorizer)),
            ("clf", RandomForestClassifier(
                n_estimators=200, class_weight="balanced_subsample", random_state=42,
            )),
        ]),
        "Neural Network": Pipeline([
            ("tfidf", TfidfVectorizer(**vectorizer)),
            ("clf", MLPClassifier(
                hidden_layer_sizes=(64, 32), max_iter=500,
                early_stopping=True, random_state=42,
            )),
        ]),
    }


def main() -> None:
    if not INPUT.is_file():
        raise SystemExit(f"Input export not found: {INPUT}")
    texts, labels, groups = load_session_documents()
    if len(texts) < 10:
        raise SystemExit(f"Only {len(texts)} labeled sessions; not enough for 5-fold evaluation")

    group_count = len(set(groups))
    n_splits = min(5, group_count)
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=42)
    y_true = labels
    majority_label, majority_count = Counter(labels).most_common(1)[0]
    model_results = {}

    for name in make_models():
        y_pred = [""] * len(texts)
        for train_idx, test_idx in splitter.split(texts, labels, groups):
            model = make_models()[name]
            model.fit([texts[i] for i in train_idx], [labels[i] for i in train_idx])
            predictions = model.predict([texts[i] for i in test_idx])
            for idx, prediction in zip(test_idx, predictions):
                y_pred[idx] = str(prediction)
        report = classification_report(
            y_true, y_pred, labels=CLASSES, output_dict=True, zero_division=0,
        )
        model_results[name] = {
            "accuracy_percent": round(100 * accuracy_score(y_true, y_pred), 2),
            "macro_f1_percent": round(100 * f1_score(
                y_true, y_pred, labels=CLASSES, average="macro", zero_division=0,
            ), 2),
            "per_class": {
                cls: {
                    "support_sessions": int(report[cls]["support"]),
                    "precision_percent": round(100 * report[cls]["precision"], 2),
                    "recall_percent": round(100 * report[cls]["recall"], 2),
                    "f1_percent": round(100 * report[cls]["f1-score"], 2),
                }
                for cls in CLASSES
            },
            "confusion_matrix_rows_true_columns_predicted": confusion_matrix(
                y_true, y_pred, labels=CLASSES,
            ).tolist(),
        }

    summary = {
        "evaluation": "5-fold stratified group cross-validation; one document per session",
        "target": "GAD-7-derived four-band severity label; not a clinical diagnosis",
        "input_rows": sum(1 for _ in csv.DictReader(INPUT.open("r", encoding="utf-8-sig", newline=""))),
        "session_count": len(texts),
        "group_count": group_count,
        "majority_baseline": {
            "predicted_class": majority_label,
            "accuracy_percent": round(100 * majority_count / len(labels), 2),
        },
        "session_counts_by_gad7_band": dict(Counter(labels)),
        "majority_baseline": {
            "predicted_class": majority_label,
            "accuracy_percent": round(100 * majority_count / len(labels), 2),
        },
        "classes": CLASSES,
        "models": model_results,
        "limitations": [
            "GAD-7 provides four severity bands, so this does not evaluate the SOP's Crisis class.",
            "Only 78 sessions are available; minimal has 8 sessions, so estimates are imprecise.",
            "Anonymous participant identity is unavailable in the export; those sessions are grouped individually.",
            "This separate experiment does not alter GAIDA's production intent classifier.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({
        "report": str(OUTPUT),
        "session_count": len(texts),
        "group_count": group_count,
        "session_counts_by_gad7_band": dict(Counter(labels)),
        "models": {
            name: {
                "accuracy_percent": values["accuracy_percent"],
                "macro_f1_percent": values["macro_f1_percent"],
            }
            for name, values in model_results.items()
        },
        "limitation": "Four GAD-7 bands only; no linked counselor crisis labels, so no five-class/Crisis accuracy claim.",
    }, indent=2))


if __name__ == "__main__":
    main()
