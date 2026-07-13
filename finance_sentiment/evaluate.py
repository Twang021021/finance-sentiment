"""
Compares the analyzer's predictions against a human-labeled dataset and
reports Accuracy, Precision, and F1-score.

See CLAUDE.md for the exact format the labeled CSV needs to be in.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score, precision_score

from .analyzer import SentimentAnalyzer

LABELS = ["negative", "neutral", "positive"]


def score_to_label(net_score: int) -> str:
    """
    Turn a document's net_score into a positive/negative/neutral label.

    This is the decision rule used for evaluation today: more positive
    words than negative -> "positive", more negative -> "negative",
    otherwise "neutral". If weighted scoring or negation handling change
    how net_score/weighted_score behave, this is the one place that would
    need a matching update.
    """
    if net_score > 0:
        return "positive"
    if net_score < 0:
        return "negative"
    return "neutral"


def evaluate(labeled_csv_path: str | Path, analyzer: SentimentAnalyzer) -> dict:
    """
    Run `analyzer` over every row of a labeled CSV (columns: text, label)
    and return a dict with accuracy, macro-averaged precision and F1, a
    full per-class report, and the raw true/predicted label lists.
    """
    data = pd.read_csv(labeled_csv_path)

    if "text" not in data.columns or "label" not in data.columns:
        raise ValueError(
            "Labeled CSV must have 'text' and 'label' columns. "
            f"Found columns: {list(data.columns)}"
        )

    true_labels = data["label"].astype(str).str.strip().str.lower().tolist()
    predicted_labels = [
        score_to_label(analyzer.analyze(str(text)).net_score) for text in data["text"]
    ]

    accuracy = accuracy_score(true_labels, predicted_labels)
    precision_macro = precision_score(
        true_labels, predicted_labels, labels=LABELS, average="macro", zero_division=0
    )
    f1_macro = f1_score(
        true_labels, predicted_labels, labels=LABELS, average="macro", zero_division=0
    )
    report_text = classification_report(
        true_labels, predicted_labels, labels=LABELS, zero_division=0
    )

    return {
        "accuracy": accuracy,
        "precision_macro": precision_macro,
        "f1_macro": f1_macro,
        "report_text": report_text,
        "true_labels": true_labels,
        "predicted_labels": predicted_labels,
    }


def format_report(results: dict) -> str:
    """Turn the dict from evaluate() into a readable multi-line string."""
    lines = [
        f"Accuracy:               {results['accuracy']:.3f}",
        f"Precision (macro avg):  {results['precision_macro']:.3f}",
        f"F1-score (macro avg):   {results['f1_macro']:.3f}",
        "",
        "Per-class breakdown:",
        results["report_text"],
    ]
    return "\n".join(lines)
