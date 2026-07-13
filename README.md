# Finance Sentiment Analyzer

A lexicon-based sentiment analysis tool for finance/stock articles. It scores text
by looking up each word against the **Loughran-McDonald (LM) financial sentiment
word list** — a word list built specifically for financial text, so words like
"liability" or "tax" aren't treated as negative just because they sound negative
in everyday English.

This is a lexicon lookup, not machine learning: a word either is or isn't in the
list, and the tool reports which words matched, how many, and a simple score.

## What it does

- **Analyze** a folder of `.txt` articles and get, per article: how many positive
  and negative words were found, the actual words, and a net/weighted score.
- **Evaluate** the tool's predictions against a labeled dataset, reporting
  Accuracy, Precision, and F1-score.

## Setup

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

### Analyze articles

Put `.txt` files in `data/input/` (this folder is gitignored, since article text you
drop in there is often copyrighted news content — see "Sample articles" below for a
safe-to-commit set to try the tool with), then run:

```
python main.py analyze --input data/input --output results.csv
```

This writes one row per article to `results.csv` with columns:
`filename, positive_count, negative_count, positive_words, negative_words,
net_score, weighted_score`. Word lists are semicolon-separated within their cell.

### Evaluate against labeled data

```
python main.py evaluate --labeled examples/labeled_sample.csv
```

This prints Accuracy, macro-averaged Precision, macro-averaged F1-score, and a
per-class precision/recall/F1 breakdown.

#### Labeled data format

A CSV with exactly two columns, `text` and `label`:

```
text,label
"Profits soared and the outlook is strong.",positive
"The company defaulted on its debt.",negative
"The board will meet next Tuesday.",neutral
```

- `text`: the raw article text, one article per row.
- `label`: one of `positive`, `negative`, or `neutral` (case-insensitive).

The tool turns each article's `net_score` (positive word count minus negative
word count) into a predicted label — above zero is positive, below zero is
negative, exactly zero is neutral — and compares that against your `label`
column to compute the metrics.

### Run the tests

```
pytest
```

### Sample articles

`data/input/` is gitignored — anything you drop there (like real news articles)
stays local and is never committed. A small set of made-up sample articles that
*are* safe to commit lives in `examples/sample_articles/`. To try the tool out:

```
cp examples/sample_articles/*.txt data/input/
python main.py analyze --input data/input --output results.csv
```

## Project layout

```
main.py                        CLI entry point
finance_sentiment/
  lexicon.py                    loads the LM word list into a word -> weight dict
  tokenizer.py                   splits article text into lowercase words
  analyzer.py                    core logic: text -> counts, word lists, scores
  negation.py                    placeholder for future negation handling
  io_utils.py                    reads .txt article files, writes the results CSV
  evaluate.py                    compares predictions against a labeled dataset
data/input/                     drop .txt article files here to be analyzed (gitignored)
examples/sample_articles/       made-up sample articles, safe to commit
examples/labeled_sample.csv     example labeled dataset for the evaluate command
tests/                          pytest tests for the modules above
```

## Extension points

The code is structured to support two future improvements without rewriting
existing modules:

- **Weighted scoring** — `lexicon.py` returns a `word -> weight` dictionary
  (currently every word is +1.0 or -1.0), and `analyzer.py` already sums these
  into a `weighted_score` field. Editing weights in `lexicon.py` (e.g. making
  "bankruptcy" worth -3.0) automatically flows through.
- **Negation handling** — `negation.py` has an `is_negated()` hook that
  `analyzer.py` already calls per word, currently a no-op. Implementing it there
  would let "not good" stop counting "good" as positive.

## Word list source, licensing, and citation

The LM Master Dictionary is obtained via the [`pysentiment2`](https://pypi.org/project/pysentiment2/)
package, which bundles the dictionary as a CSV file (no manual download needed).

The dictionary itself is created and maintained by Tim Loughran and Bill McDonald
at the University of Notre Dame. Per their terms
(https://sraf.nd.edu/loughranmcdonald-master-dictionary/), the word list is **free
to use for academic and personal research purposes**. **Commercial use requires a
license from the University of Notre Dame** — contact the maintainers via the link
above before using this tool's output in a commercial product or service.

If you publish research using this word list, cite:

> Loughran, T. and McDonald, B. (2011), "When Is a Liability Not a Liability?
> Textual Analysis, Dictionaries, and 10-Ks," *Journal of Finance*, 66: 35-65.