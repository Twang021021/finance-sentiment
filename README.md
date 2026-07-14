# Finance Sentiment Analyzer

A lexicon-based sentiment analysis tool for finance/stock articles. It scores text
by looking up each word against the **Loughran-McDonald (LM) financial sentiment
word list** — a word list built specifically for financial text, so words like
"liability" or "tax" aren't treated as negative just because they sound negative
in everyday English. Words LM doesn't cover can be added to a small, hand-approved
supplement list (see `supplement_lexicon.csv`) — there's a built-in command to
help you find good candidates from the general-purpose Harvard IV-4 dictionary,
but nothing from it is trusted automatically (see CLAUDE.md for why).

This is a lexicon lookup, not machine learning: matching also accounts for
inflected forms (via lemmatization), negation ("not good"), intensifiers
("sharply") and diminishers ("slightly"), and directional words whose sentiment
depends on a nearby topic noun ("profits fell" is negative, "costs fell" is
positive) — see CLAUDE.md for exactly how each works and their limitations.

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
negated_words, intensified_words, diminished_words, directional_words,
net_score, weighted_score`. Word lists are semicolon-separated within their
cell, and each word is tagged `word[SOURCE:MATCH]` — its source lexicon
("LM"/"SUPP"/"TOPIC") and whether it matched exactly or via its lemma (base
form), e.g. `surged[SUPP:exact]; declining[LM:lemma]; fell[TOPIC:exact]`.
Lemma matches are worth a second look — they're the ones that can drift in
meaning (see CLAUDE.md for a real example: "latest" incorrectly matching via
its lemma "late"). The last four columns are each context rule's audit trail —
e.g. `negated_words` lists phrases like `not good`, `directional_words` lists
phrases like `profits fell` — so every rule's effect is separately auditable.

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

### Find candidate words for the supplement list

```
python main.py suggest-supplement --input data/input --output supplement_candidates.csv
```

Scans your articles for words that would match Harvard IV-4 but aren't already
covered by LM or your current supplement list, and writes them out with their
frequency so you can review the most impactful ones first. This never edits
`finance_sentiment/supplement_lexicon.csv` itself — approved words go in there by
hand (two columns: `word,weight`). See CLAUDE.md for how the starter list was
built and what was deliberately left out.

### Audit lemma-driven matches

```
python main.py lemma-report --input data/input
```

Lists every word that matched only via its lemma (base form), not its exact
spelling — the ones most likely to have drifted in meaning (e.g. "latest"
incorrectly matching through "late" before it was excluded — see CLAUDE.md).
Read-only, prints straight to the console.

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
  lexicon.py                    loads LM (primary) + your approved supplement
                                list into one word -> (weight, source) lookup;
                                also loads Harvard IV-4 for suggest-supplement
  supplement_lexicon.csv         your hand-approved extra words (word,weight)
  tokenizer.py                   splits article text into lowercase words
  lemmatizer.py                   reduces a word to its base form for lookups
  context_rules.py                shared shape for the three rules below
  negation.py                     flips polarity after cues like "not"
  intensifiers.py                 words like "sharply" that amplify a nearby word
  diminishers.py                  words like "slightly" that shrink a nearby word
  directional.py                  words like "rose"/"fell" resolved via a topic noun
  analyzer.py                     core logic: text -> counts, word lists, scores
  io_utils.py                     reads .txt article files, writes the results CSV
  evaluate.py                     compares predictions against a labeled dataset
data/input/                     drop .txt article files here to be analyzed (gitignored)
examples/sample_articles/       made-up sample articles, safe to commit
examples/labeled_sample.csv     example labeled dataset for the evaluate command
tests/                          pytest tests for the modules above
```

See CLAUDE.md for a full explanation of matching, negation, intensifiers, why
Harvard IV-4 isn't merged in automatically (measured: 51-76% of matches on real
articles, including plainly neutral words), and a documented gap: common
financial-news words like "plunged," "tumbled," and "rout" aren't reliably
covered by any established lexicon we checked (LM, Harvard IV-4, VADER,
SentiWordNet) — LM was built from formal SEC filing language, not news-headline
vocabulary.

## Extension points

- **Weighted scoring** — `lexicon.py` returns a `word -> LexiconEntry(weight,
  source)` dictionary (currently every word is +1.0 or -1.0), and `analyzer.py`
  already sums these into a `weighted_score` field. Editing weights in
  `lexicon.py` (e.g. making "bankruptcy" worth -3.0) automatically flows through.
- **Intensifier/diminisher strength** — `intensifiers.py`'s and
  `diminishers.py`'s multipliers are easy to tune per word.
- **New context rules** — any rule that scales a matched word's weight based on
  a nearby cue word is one new module plus one line in `analyzer.py`'s
  `CONTEXT_RULES` list (see CLAUDE.md's "Context rules" section).
- **New topic nouns/directional words** — `directional.py`'s topic-noun lists
  and directional-word set are plain sets/dicts, easy to extend.
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

The **Harvard IV-4 / General Inquirer** dictionary (used only to suggest
supplement-list candidates — see CLAUDE.md) is also bundled by `pysentiment2` and
is separately maintained by Harvard University; see
https://inquirer.sites.fas.harvard.edu/ for its own terms and background before
relying on it commercially.