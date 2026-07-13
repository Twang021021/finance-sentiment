# Finance Sentiment Analyzer

## Working with this user

**Communication style.** Whenever you make a code change, explain it in plain
language — what changed, why, and what it means for how the tool behaves.
Prefer clear explanations over terse diffs, and briefly define specialized
terminology the first time it comes up.

## What this project does

Given finance/stock articles, it looks up each word against the **Loughran-McDonald
(LM) financial sentiment word list** and reports which words are positive, which are
negative, and how many of each. It's a lexicon-based approach: no machine learning,
just "is this word in the list."

## Where the word list comes from

The LM Master Dictionary is a word list built by Tim Loughran and Bill McDonald at
the University of Notre Dame specifically for financial text (it's aware that words
like "liability" or "tax" aren't actually negative in a 10-K filing, unlike in
everyday English). We get it via the `pysentiment2` pip package, which bundles the
official CSV — no manual download needed. See `finance_sentiment/lexicon.py` for
exactly how it's loaded. If you ever publish analysis based on this word list, cite:
Loughran, T. and McDonald, B. (2011), "When Is a Liability Not a Liability?" *Journal
of Finance*. More info: https://sraf.nd.edu/loughranmcdonald-master-dictionary/

Important detail: we do **not** use pysentiment2's own scoring code, because it stems
words (e.g. turns "abandoned" into "abandon") before matching, which would make the
"words found" output confusing. Instead, `lexicon.py` reads the bundled CSV directly
and matches whole words as they actually appear, lowercase.

## Project layout

```
main.py                     CLI entry point (run this)
finance_sentiment/
  lexicon.py                 loads the LM word list into a word -> weight dict
  tokenizer.py                splits article text into lowercase words
  analyzer.py                 core logic: text -> counts, word lists, scores
  negation.py                 placeholder for future negation handling (see below)
  io_utils.py                 reads .txt article files, writes the results CSV
  evaluate.py                 compares predictions against a labeled dataset
data/input/                  drop .txt article files here to be analyzed (gitignored)
examples/sample_articles/    made-up sample articles that are safe to commit
examples/labeled_sample.csv  example labeled dataset for the evaluate command
tests/                       pytest tests for the modules above
```

`data/input/` is gitignored on purpose — real news articles dropped there for testing
are often copyrighted, so they should stay local and never get committed. The three
original made-up sample articles live in `examples/sample_articles/` instead, which
*is* tracked. To try the tool with them: `cp examples/sample_articles/*.txt data/input/`
before running `analyze`.

## Setup

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Running it

Analyze every `.txt` file in a folder and write one CSV row per article:

```
python main.py analyze --input data/input --output results.csv
```

The output CSV has columns: `filename, positive_count, negative_count,
positive_words, negative_words, net_score, weighted_score`. Word lists are
semicolon-separated inside their cell.

Evaluate against a labeled dataset (see format below):

```
python main.py evaluate --labeled examples/labeled_sample.csv
```

This prints Accuracy, macro-averaged Precision, macro-averaged F1-score, and a
per-class breakdown.

Run the test suite:

```
pytest
```

## Labeled data format (for `evaluate`)

A CSV with exactly two columns, `text` and `label`:

```
text,label
"Profits soared and the outlook is strong.",positive
"The company defaulted on its debt.",negative
"The board will meet next Tuesday.",neutral
```

- `text`: the raw article text, one article per row.
- `label`: one of `positive`, `negative`, or `neutral` (case doesn't matter).

The analyzer turns its `net_score` (positive word count minus negative word count)
into a predicted label using this rule (see `score_to_label` in `evaluate.py`):
above zero is positive, below zero is negative, exactly zero is neutral. That
predicted label is then compared against your `label` column to compute the metrics.

## Extension points already built into the code

These aren't implemented yet, but the code is structured so adding them later
shouldn't require rewriting other files:

- **Weighted scoring.** `lexicon.py` already returns a `word -> weight` dictionary
  (currently every word is +1.0 or -1.0) instead of two plain lists. `analyzer.py`
  already sums these weights into a `weighted_score` field. To make some words count
  more than others (e.g. "bankruptcy" = -3.0), just edit the weights in
  `lexicon.py` — `analyzer.py` and everything downstream will pick it up automatically.
- **Negation handling.** `negation.py` has a `is_negated(tokens, index)` function
  that `analyzer.py` already calls for every matched word, but it currently always
  returns `False`, so it has no effect. To implement real negation (so "not good"
  stops counting "good" as positive), that function is the one place to change —
  look at the words just before `tokens[index]` for something in `NEGATION_WORDS`.
