import csv

from finance_sentiment.analyzer import AnalysisResult, MatchedWord
from finance_sentiment.io_utils import write_results_csv, write_supplement_candidates_csv


def test_write_results_csv_includes_source_and_negated_words(tmp_path):
    output_path = tmp_path / "results.csv"
    result = AnalysisResult(
        positive_count=1,
        negative_count=1,
        positive_words=[MatchedWord("surged", "SUPP")],
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
    assert row["positive_words"] == "surged[SUPP:exact]"
    assert row["negative_words"] == "good[LM:exact]"
    assert row["negated_words"] == "not good"


def test_write_results_csv_tags_lemma_matches(tmp_path):
    output_path = tmp_path / "results.csv"
    result = AnalysisResult(
        positive_count=0,
        negative_count=1,
        negative_words=[MatchedWord("declining", "LM", "lemma")],
        net_score=-1,
        weighted_score=-1.0,
    )
    write_results_csv({"article.txt": result}, output_path)

    with open(output_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert rows[0]["negative_words"] == "declining[LM:lemma]"


def test_write_results_csv_includes_context_rule_audit_columns(tmp_path):
    output_path = tmp_path / "results.csv"
    result = AnalysisResult(
        positive_count=0,
        negative_count=1,
        negative_words=[MatchedWord("fell", "TOPIC")],
        intensified_words=["losses mounted sharply"],
        diminished_words=["margins slightly weakened"],
        directional_words=["profits fell"],
        net_score=-1,
        weighted_score=-1.0,
    )
    write_results_csv({"article.txt": result}, output_path)

    with open(output_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    row = rows[0]
    assert row["negative_words"] == "fell[TOPIC:exact]"
    assert row["intensified_words"] == "losses mounted sharply"
    assert row["diminished_words"] == "margins slightly weakened"
    assert row["directional_words"] == "profits fell"


def test_write_supplement_candidates_csv(tmp_path):
    output_path = tmp_path / "candidates.csv"
    write_supplement_candidates_csv([("surge", 1.0, 3), ("dumped", -1.0, 1)], output_path)

    with open(output_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert rows == [
        {"word": "surge", "hiv4_weight": "1.0", "frequency": "3"},
        {"word": "dumped", "hiv4_weight": "-1.0", "frequency": "1"},
    ]