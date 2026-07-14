# Finance Sentiment Analyzer

A lexicon-based sentiment analysis tool for finance/stock articles. It scores text
by looking up each word against the **Loughran-McDonald (LM) financial sentiment
word list** — a word list built specifically for financial text, so words like
"liability" or "tax" aren't treated as negative just because they sound negative
in everyday English. Words LM doesn't cover fall back to the general-purpose
Harvard IV-4 dictionary.

This is a lexicon lookup, not machine learning: matching also accounts for
inflected forms (via lemmatization), negation ("not good"), and intensifiers
("sharply") — see CLAUDE.md for exactly how each works and their limitations.

## What it does

- **Analyze** a folder of `.txt` articles and get, per article: how many positive
  and negative words were found, the actual words (each tagged with which lexicon
  it matched from), any negated phrases, and a net/weighted score.
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
negated_words, net_score, weighted_score`. Word lists are semicolon-separated
within their cell, and each word is tagged with its source lexicon, e.g.
`surged[HIV4]; profitable[LM]`. `negated_words` lists phrases like `not good` so
you can audit any word whose polarity got flipped by negation.

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
  lexicon.py                    loads LM (primary) + Harvard IV-4 (fallback) into
                                one word -> (weight, source) lookup
  tokenizer.py                   splits article text into lowercase words
  lemmatizer.py                   reduces a word to its base form for lookups
  negation.py                     flips polarity after cues like "not"
  intensifiers.py                 words like "sharply" that amplify a nearby word
  analyzer.py                     core logic: text -> counts, word lists, scores
  io_utils.py                     reads .txt article files, writes the results CSV
  evaluate.py                     compares predictions against a labeled dataset
data/input/                     drop .txt article files here to be analyzed (gitignored)
examples/sample_articles/       made-up sample articles, safe to commit
examples/labeled_sample.csv     example labeled dataset for the evaluate command
tests/                          pytest tests for the modules above
```

See CLAUDE.md for a full explanation of matching, negation, intensifiers, the
LM/Harvard IV-4 merge, and a documented gap: common financial-news words like
"plunged," "tumbled," and "rout" aren't reliably covered by any established lexicon
we checked (LM, Harvard IV-4, VADER, SentiWordNet) — LM was built from formal SEC
filing language, not news-headline vocabulary.

## Extension points

- **Weighted scoring** — `lexicon.py` returns a `word -> LexiconEntry(weight,
  source)` dictionary (currently every word is +1.0 or -1.0), and `analyzer.py`
  already sums these into a `weighted_score` field. Editing weights in
  `lexicon.py` (e.g. making "bankruptcy" worth -3.0) automatically flows through.
- **Intensifier strength** — `intensifiers.py`'s multiplier (1.5x by default) is
  easy to tune per word.
- **Negation dampening** — negation currently fully flips a word's sign; a
  softer, magnitude-reducing version is a natural next step once weights are more
  than just ±1.

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

The **Harvard IV-4 / General Inquirer** dictionary (used as a fallback — see
CLAUDE.md) is also bundled by `pysentiment2` and is separately maintained by
Harvard University; see https://inquirer.sites.fas.harvard.edu/ for its own terms
and background before relying on it commercially.