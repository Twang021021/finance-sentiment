"""
Command-line entry point for the finance sentiment analyzer.

Usage:
    python main.py analyze --input data/input --output results.csv
    python main.py evaluate --labeled examples/labeled_sample.csv
    python main.py suggest-supplement --input data/input --output supplement_candidates.csv
    python main.py lemma-report --input data/input
"""

from __future__ import annotations

import argparse

from finance_sentiment.analyzer import SentimentAnalyzer
from finance_sentiment.evaluate import evaluate, format_report
from finance_sentiment.io_utils import (
    read_articles_from_folder,
    write_results_csv,
    write_supplement_candidates_csv,
)
from finance_sentiment.lexicon import (
    find_lemma_matches,
    load_combined_lexicon,
    suggest_supplement_candidates,
)


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


def run_suggest_supplement(input_folder: str, output_path: str) -> None:
    articles = read_articles_from_folder(input_folder)
    if not articles:
        print(f"No .txt files found in {input_folder}")
        return

    candidates = suggest_supplement_candidates(articles)
    write_supplement_candidates_csv(candidates, output_path)
    print(
        f"Found {len(candidates)} candidate word(s) not covered by LM or the "
        f"current supplement list. Written to {output_path} for your review.\n"
        "Approved words go in finance_sentiment/supplement_lexicon.csv "
        "(columns: word,weight)."
    )


def run_lemma_report(input_folder: str) -> None:
    articles = read_articles_from_folder(input_folder)
    if not articles:
        print(f"No .txt files found in {input_folder}")
        return

    matches = find_lemma_matches(articles)
    if not matches:
        print("No lemma-path matches found.")
        return

    print(f"{len(matches)} unique lemma-path match(es), most frequent first:\n")
    for surface_word, lemma, weight, source, frequency in matches:
        print(
            f"  {surface_word} -> {lemma}  "
            f"(weight={weight}, lexicon={source}, frequency={frequency})"
        )


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

    suggest_parser = subparsers.add_parser(
        "suggest-supplement",
        help="Scan articles for Harvard IV-4 words not covered by LM/the supplement list, for your review.",
    )
    suggest_parser.add_argument("--input", required=True, help="Folder containing .txt article files.")
    suggest_parser.add_argument(
        "--output", required=True, help="Path to write the candidate words CSV."
    )

    lemma_report_parser = subparsers.add_parser(
        "lemma-report",
        help="List every word that matched the lexicon via its lemma, for auditing semantic drift.",
    )
    lemma_report_parser.add_argument(
        "--input", required=True, help="Folder containing .txt article files."
    )

    args = parser.parse_args()

    if args.command == "analyze":
        run_analyze(args.input, args.output)
    elif args.command == "evaluate":
        run_evaluate(args.labeled)
    elif args.command == "suggest-supplement":
        run_suggest_supplement(args.input, args.output)
    elif args.command == "lemma-report":
        run_lemma_report(args.input)


if __name__ == "__main__":
    main()
