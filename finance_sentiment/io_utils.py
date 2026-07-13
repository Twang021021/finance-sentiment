"""
Reading article files and writing the results CSV.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .analyzer import AnalysisResult


def read_articles_from_folder(folder: str | Path) -> dict[str, str]:
    """Read every .txt file in `folder` into {filename: text}."""
    folder_path = Path(folder)
    articles: dict[str, str] = {}

    for file_path in sorted(folder_path.glob("*.txt")):
        articles[file_path.name] = file_path.read_text(encoding="utf-8")

    return articles


def write_results_csv(results: dict[str, AnalysisResult], output_path: str | Path) -> None:
    """
    Write one row per article to a CSV file with columns:
    filename, positive_count, negative_count, positive_words, negative_words,
    net_score, weighted_score.

    Word lists are joined with "; " so they fit in a single CSV cell.
    """
    fieldnames = [
        "filename",
        "positive_count",
        "negative_count",
        "positive_words",
        "negative_words",
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
                    "positive_words": "; ".join(result.positive_words),
                    "negative_words": "; ".join(result.negative_words),
                    "net_score": result.net_score,
                    "weighted_score": result.weighted_score,
                }
            )
