import csv

from finance_sentiment.analyzer import AnalysisResult, MatchedWord
from finance_sentiment.io_utils import write_results_csv


def test_write_results_csv_includes_source_and_negated_words(tmp_path):
    output_path = tmp_path / "results.csv"
    result = AnalysisResult(
        positive_count=1,
        negative_count=1,
        positive_words=[MatchedWord("surged", "HIV4")],
        negative_words=[MatchedWord("good", "LM")],
        negated_words=["not good"],
        net_score=0,
        weighted_score=0.0,
    )
    write_results_csv({"article.txt": result}, output_path)

    with open(output_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 1
    row = rows[0]
    assert row["filename"] == "article.txt"
    assert row["positive_words"] == "surged[HIV4]"
    assert row["negative_words"] == "good[LM]"
    assert row["negated_words"] == "not good"