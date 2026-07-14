"""
Reading article files and writing the results CSV.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .analyzer import AnalysisResult, MatchedWord


def read_articles_from_folder(folder: str | Path) -> dict[str, str]:
    """Read every .txt file in `folder` into {filename: text}."""
    folder_path = Path(folder)
    articles: dict[str, str] = {}

    for file_path in sorted(folder_path.glob("*.txt")):
        articles[file_path.name] = file_path.read_text(encoding="utf-8")

    return articles


def _format_matched_words(words: list[MatchedWord]) -> str:
    """Turn e.g. [MatchedWord("latest", "LM", "lemma")] into "latest[LM:lemma]", joined with "; "."""
    return "; ".join(f"{match.word}[{match.source}:{match.match_type}]" for match in words)


def write_results_csv(results: dict[str, AnalysisResult], output_path: str | Path) -> None:
    """
    Write one row per article to a CSV file with columns:
    filename, positive_count, negative_count, positive_words, negative_words,
    negated_words, intensified_words, diminished_words, directional_words,
    net_score, weighted_score.

    Each word in positive_words/negative_words is shown as word[SOURCE:MATCH],
    where SOURCE is "LM", "SUPP", or "TOPIC" (the lexicon it matched from, or
    "TOPIC" for a directional word resolved via a nearby topic noun - see
    directional.py) and MATCH is "exact" or "lemma" (whether it matched its
    exact spelling or via its base form - see lexicon.py). Word lists are
    joined with "; " so they fit in a single CSV cell.

    negated_words/intensified_words/diminished_words/directional_words each
    list the phrases that triggered that specific context rule (e.g.
    "not good", "sharply declined", "slightly improved", "profits fell"), so
    every rule's effect is separately auditable - see context_rules.py.
    """
    fieldnames = [
        "filename",
        "positive_count",
        "negative_count",
        "positive_words",
        "negative_words",
        "negated_words",
        "intensified_words",
        "diminished_words",
        "directional_words",
        "net_score",
        "weighted_score",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()

        for filename, result in results.items():
            writer.writerow(
                {
                    "filename": filename,
                    "positive_count": result.positive_count,
                    "negative_count": result.negative_count,
                    "positive_words": _format_matched_words(result.positive_words),
                    "negative_words": _format_matched_words(result.negative_words),
                    "negated_words": "; ".join(result.negated_words),
                    "intensified_words": "; ".join(result.intensified_words),
                    "diminished_words": "; ".join(result.diminished_words),
                    "directional_words": "; ".join(result.directional_words),
                    "net_score": result.net_score,
                    "weighted_score": result.weighted_score,
                }
            )


def write_supplement_candidates_csv(
    candidates: list[tuple[str, float, int]], output_path: str | Path
) -> None:
    """
    Write suggest_supplement_candidates()'s output (word, hiv4_weight,
    frequency tuples) to a CSV for review, sorted however they're passed in
    (suggest_supplement_candidates() already sorts by frequency descending).
    """
    with open(output_path, "w", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["word", "hiv4_weight", "frequency"])
        for word, weight, frequency in candidates:
            writer.writerow([word, weight, frequency])