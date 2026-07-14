"""
Command-line entry point for the finance sentiment analyzer.

Usage:
    python main.py analyze --input data/input --output results.csv
    python main.py evaluate --labeled examples/labeled_sample.csv
"""

from __future__ import annotations

import argparse

from finance_sentiment.analyzer import SentimentAnalyzer
from finance_sentiment.evaluate import evaluate, format_report
from finance_sentiment.io_utils import read_articles_from_folder, write_results_csv
from finance_sentiment.lexicon import load_combined_lexicon


def run_analyze(input_folder: str, output_path: str) -> None:
    lexicon = load_combined_lexicon()
    analyzer = SentimentAnalyzer(lexicon)

    articles = read_articles_from_folder(input_folder)
    if not articles:
        print(f"No .txt files found in {input_folder}")
        return

    results = {filename: analyzer.analyze(text) for filename, text in articles.items()}
    write_results_csv(results, output_path)
    print(f"Analyzed {len(results)} article(s). Results written to {output_path}")


def run_evaluate(labeled_csv_path: str) -> None:
    lexicon = load_combined_lexicon()
    analyzer = SentimentAnalyzer(lexicon)

    results = evaluate(labeled_csv_path, analyzer)
    print(format_report(results))


def main() -> None:
    parser = argparse.ArgumentParser(description="Lexicon-based financial sentiment analyzer.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze a folder of .txt articles.")
    analyze_parser.add_argument("--input", required=True, help="Folder containing .txt article files.")
    analyze_parser.add_argument("--output", required=True, help="Path to write the results CSV.")

    evaluate_parser = subparsers.add_parser("evaluate", help="Evaluate against a labeled dataset.")
    evaluate_parser.add_argument(
        "--labeled", required=True, help="Path to the labeled CSV (must have text,label columns)."
    )

    args = parser.parse_args()

    if args.command == "analyze":
        run_analyze(args.input, args.output)
    elif args.command == "evaluate":
        run_evaluate(args.labeled)


if __name__ == "__main__":
    main()
