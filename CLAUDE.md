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

We also merge in a second, general-purpose dictionary — **Harvard IV-4** (the
"General Inquirer" word list), also bundled free with `pysentiment2` — as a fallback
for words LM doesn't cover at all. LM always wins where both have an opinion about a
word; Harvard IV-4 only fills gaps. See "Where each matched word comes from" below.

## Project layout

```
main.py                     CLI entry point (run this)
finance_sentiment/
  lexicon.py                 loads LM (primary) + Harvard IV-4 (fallback) into one
                              word -> (weight, source) lookup
  tokenizer.py                splits article text into lowercase words
  lemmatizer.py                reduces a word to its base form for lexicon lookups
  negation.py                  flips a word's polarity if a cue like "not" precedes it
  intensifiers.py              words like "sharply" that amplify a nearby word instead
                              of carrying their own sentiment
  analyzer.py                  core logic: text -> counts, word lists, scores
  io_utils.py                  reads .txt article files, writes the results CSV
  evaluate.py                  compares predictions against a labeled dataset
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
positive_words, negative_words, negated_words, net_score, weighted_score`. Word
lists are semicolon-separated inside their cell. Each word in `positive_words`/
`negative_words` is shown as `word[SOURCE]`, e.g. `surged[HIV4]; profitable[LM]` —
see "Where each matched word comes from" below. `negated_words` lists the full
phrase (e.g. `not good`) for any word whose polarity got flipped by negation, so
you can audit those cases at a glance.

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

## How matching actually works (lemmatization)

A token is looked up two ways, in order: first its exact spelling, then — only if
that misses — its **lemma** (base/dictionary form, e.g. "declining" -> "decline"),
via `lemmatizer.py` (built on the `simplemma` library). Whichever form matched, the
word reported back to you in `positive_words`/`negative_words` is always the
**original surface word from the article**, never the lemma — so you'll see
"declining" in the output, not "decline".

We chose `simplemma` over NLTK's `WordNetLemmatizer` or spaCy: it ships its lookup
data inside the pip package itself (no extra multi-megabyte corpus download the
first time you run the tool, which NLTK's wordnet lemmatizer needs), it's pure
Python with nothing heavy to load (unlike spaCy, which needs a full trained
pipeline just for this one job), and it correctly handles irregular forms like
"sank" -> "sink" without any extra setup.

**Honest caveat:** lemmatization helps less than you might expect on this specific
lexicon. We checked, and the LM Master Dictionary already lists almost every common
inflection as its own separate entry (`decline`/`declines`/`declining`/`declined`
are all already separately in the list, for example) — LM was built by counting
words that actually appear in SEC filings, so common inflected forms were already
swept up individually. Lemmatization is a safety net for less common forms, not a
big new source of matches.

## Negation handling

If a sentiment word is preceded within 3 tokens by a cue word ("not", "no",
"never", "without", "hardly", ...; see `NEGATION_WORDS` in `negation.py`), its
polarity is **flipped** rather than just zeroed out. E.g. "not good" counts as
negative, not neutral.

Why flip instead of suppress? "Not good" reads to a person as leaning negative,
not neutral — suppressing would throw that signal away entirely. Flipping is the
standard simple heuristic in rule-based sentiment systems (it's also the basis for
VADER's negation handling). It's not perfect — "not terrible" doesn't really mean
"great" the way a flip implies — but with a lexicon of only +1/-1 weights (not a
continuous scale), flipping the sign is the simplest rule that still points in the
right direction. Every flipped case is listed in the `negated_words` output column
(e.g. `not good`) so you can spot-check whether the heuristic got it right.

## Intensifiers

A handful of LM words are pure degree/magnitude modifiers rather than words with
sentiment of their own — "sharply" isn't good or bad by itself, it just makes
whatever's next to it more extreme ("sharply higher" vs. "sharply lower"). Counting
"sharply" as its own negative word (which the LM list otherwise implies) would
double-count sentiment and mislabel phrases like "sharply higher" as negative
overall.

`intensifiers.py` lists six such words we identified this way: `sharply`,
`severely`, `drastically` (previously counted as their own LM-negative words) and
`greatly`, `tremendously`, `exceptionally` (previously LM-positive). These never
appear in `positive_words`/`negative_words` and never affect `net_score` — instead,
when one is adjacent (within 2 tokens) to a sentiment word, it multiplies that
word's weight by 1.5x, which shows up in `weighted_score` only.

We deliberately kept this list narrow. Some similar-looking LM words were left out
because they carry their own judgment even with nothing to modify — e.g.
"excessively," "unduly," and "grossly" all imply "more than is acceptable," which
is itself a negative judgment, not just a magnitude.

## Where each matched word comes from (LM vs. Harvard IV-4)

Every matched word's source lexicon is shown in the output as `word[LM]` or
`word[HIV4]`. `lexicon.py`'s `load_combined_lexicon()` builds this: it starts from
LM, then adds any Harvard IV-4 word LM doesn't already have an opinion on. LM always
wins on overlap.

Harvard IV-4 is a general-purpose (not finance-specific) dictionary, so it's
strictly a fallback, and it's less precise than LM. Two things worth knowing about
how it's filtered (see `load_hiv4_lexicon()` for the exact logic):
- A Harvard IV-4 word can have several numbered "senses" (e.g. `COMPANY#1` the
  business entity vs. `COMPANY#2` the fact of being with someone), and only some
  senses may be tagged positive/negative. We only trust a word's **most common**
  sense (`#1`, or its only sense if unnumbered) — e.g. "company" is correctly
  excluded because its `#1` sense isn't tagged, even though its rarer `#2` sense
  happens to be tagged positive. Trusting anything past `#1` would just be guessing
  at which meaning is intended.
- Even with that filter, false positives happen for finance-neutral words that
  carry unrelated everyday connotations — and on real news articles this turned
  out to be a bigger effect than expected, not just an occasional edge case. We
  tested on 3 real articles: **51-76% of all matched words came from HIV-4, not
  LM** — words like `share`, `main`, `open`, `interest`, `war`, `cost`, and `need`
  all got tagged as sentiment words, which a finance-aware reader wouldn't count.
  HIV-4 has roughly 3,600 tagged words vs. LM's ~2,700, and general news prose
  uses a lot more everyday vocabulary than the formal filing language LM was built
  from — so HIV-4's breadth ends up dominating by sheer word count, even though LM
  always wins on any word both lexicons agree on. In practice this means
  `weighted_score`/`net_score` are now driven more by generic-English sentiment
  than finance-specific judgment. If this matters for your use case, the fix is
  to add specific noisy words to a small excluded-words list in `lexicon.py`
  (not implemented yet), or to drop the HIV-4 fallback and rely on LM alone
  (`load_lm_lexicon()` + manually build a `LexiconEntry` dict, or just skip the
  `load_combined_lexicon()` call in `main.py`) if precision matters more than
  covering LM's gaps.

### Words we still can't catch, and why

Words like "plunged," "tumbled," "sank" (now caught via HIV-4, see below),
"selloff," and "rout" are common in financial *news* but were largely absent from
both lexicons we checked:

- **LM**: none of `plunge`, `tumble`, `sink`, `rout`, `selloff` (in any inflection)
  appear at all. This isn't a matching-technique problem lemmatization can fix —
  the words simply aren't in the list. That's because LM was built from formal SEC
  filing language ("declined," "adversely affected"), not news-headline vocabulary
  ("plunged," "tumbled").
- **Harvard IV-4**: partially helps — `sank` and `slump` are tagged negative,
  `surge` and `rally` are tagged positive (all four now flow through the fallback
  merge above) — but `plunge`, `tumble`, `sink` (base form), `rout`, and `selloff`
  are still untagged.
- **VADER** (checked, not merged in): only `crash` is present; everything else is
  absent. VADER's ~7,500-word lexicon skews toward social-media/informal language.
- **SentiWordNet** (checked, not merged in): scores nearly all of these words as
  "objective"/neutral, even senses whose definitions literally say "decline
  markedly" or "suffer a sudden downfall." It's automatically derived from WordNet
  glosses, and physical-motion verbs like "sink" or "plunge" aren't inherently
  emotionally loaded in general English — their negative meaning is specific to the
  financial context, which is exactly the kind of domain nuance general lexicons
  don't capture (ironically, the same reason LM had to be built in the first
  place).

**Bottom line:** there's no clean off-the-shelf lexicon that closes this gap. If
this news-headline vocabulary matters for your use case, the realistic path is a
small, explicitly-labeled supplementary word list (e.g. 20-30 market-movement
verbs) added deliberately to `lexicon.py`, clearly separated from LM/HIV-4 rather
than blended in — that's a manual step, but a small, visible, auditable one, not
ad hoc lexicon pollution.

## Extension points already built into the code

- **Weighted scoring.** `lexicon.py` returns a `word -> LexiconEntry(weight, source)`
  dictionary (currently every word is +1.0 or -1.0) instead of two plain lists.
  `analyzer.py` already sums these weights into a `weighted_score` field. To make
  some words count more than others (e.g. "bankruptcy" = -3.0), just edit the
  weights in `lexicon.py` — `analyzer.py` and everything downstream will pick it up
  automatically.
- **Intensifier strength.** `intensifiers.py`'s `DEFAULT_MULTIPLIER` (1.5) and the
  per-word `INTENSIFIER_WORDS` dict are both easy to tune independently per word.
- **Negation dampening.** Right now negation fully flips a word's sign. A more
  nuanced version (dampen the magnitude instead of a full flip, similar to how
  VADER does it) would only require changing `negation.py`'s effect on `weight` in
  `analyzer.py`, once weights are more than just ±1.
