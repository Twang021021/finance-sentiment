import csv

from finance_sentiment.analyzer import SentimentAnalyzer
from finance_sentiment.evaluate import evaluate, score_to_label

TEST_LEXICON = {
    "profitable": 1.0,
    "strong": 1.0,
    "bankruptcy": -1.0,
    "losses": -1.0,
}


def test_score_to_label():
    assert score_to_label(2) == "positive"
    assert score_to_label(-1) == "negative"
    assert score_to_label(0) == "neutral"


def test_evaluate_perfect_predictions(tmp_path):
    csv_path = tmp_path / "labeled.csv"
    rows = [
        ("The results were profitable and strong.", "positive"),
        ("The company faced bankruptcy and losses.", "negative"),
        ("The meeting is scheduled for Tuesday.", "neutral"),
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "label"])
        writer.writerows(rows)

    analyzer = SentimentAnalyzer(TEST_LEXICON)
    results = evaluate(csv_path, analyzer)

    assert results["accuracy"] == 1.0
    assert results["precision_macro"] == 1.0
    assert results["f1_macro"] == 1.0


def test_evaluate_requires_text_and_label_columns(tmp_path):
    csv_path = tmp_path / "bad.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["body", "sentiment"])
        writer.writerow(["some text", "positive"])

    analyzer = SentimentAnalyzer(TEST_LEXICON)
    try:
        evaluate(csv_path, analyzer)
        assert False, "expected a ValueError"
    except ValueError:
        pass
