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

We also use a second, general-purpose dictionary — **Harvard IV-4** (the "General
Inquirer" word list), also bundled free with `pysentiment2` — but *not* merged in
automatically. Harvard IV-4 turned out to be too noisy for that (see "Where each
matched word comes from" below for why); instead it's used to *suggest* candidate
words for a small, hand-approved supplement list. See "Building the supplement
list" below.

## Project layout

```
main.py                        CLI entry point (run this)
finance_sentiment/
  lexicon.py                    loads LM (primary) + your approved supplement list
                                 into one word -> (weight, source) lookup; also
                                 loads Harvard IV-4 for the suggest-supplement scan
  supplement_lexicon.csv         your hand-approved extra words (word,weight) -
                                 edit this directly to add/remove words
  tokenizer.py                   splits article text into lowercase words
  lemmatizer.py                   reduces a word to its base form for lexicon lookups
  context_rules.py                shared RuleEffect shape used by the three
                                 context rules below (see "Context rules" below)
  negation.py                     flips a word's polarity if a cue like "not" precedes it
  intensifiers.py                 words like "sharply" that amplify a nearby word instead
                                 of carrying their own sentiment
  diminishers.py                  words like "slightly" that shrink a nearby word's weight
  directional.py                  words like "rose"/"fell" whose sentiment depends on a
                                 nearby topic noun (see "Directional words" below)
  analyzer.py                     core logic: text -> counts, word lists, scores
  io_utils.py                     reads .txt article files, writes the results CSV
  evaluate.py                     compares predictions against a labeled dataset
data/input/                     drop .txt article files here to be analyzed (gitignored)
examples/sample_articles/       made-up sample articles that are safe to commit
examples/labeled_sample.csv     example labeled dataset for the evaluate command
tests/                          pytest tests for the modules above
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
positive_words, negative_words, negated_words, intensified_words,
diminished_words, directional_words, net_score, weighted_score`. Word lists are
semicolon-separated inside their cell. Each word in `positive_words`/
`negative_words` is shown as `word[SOURCE:MATCH]`, e.g. `surged[SUPP:exact]`,
`declining[LM:lemma]`, `fell[TOPIC:exact]` — SOURCE is which lexicon it matched
from ("LM", "SUPP", or "TOPIC" for a directional word resolved via a nearby
topic noun — see "Directional words" below), MATCH is whether it matched its
exact spelling or via its lemma/base form (see "How matching actually works"
below — lemma matches are worth auditing since that's where semantic drift like
"latest"->"late" can sneak in). The last four of those columns are the **context
rules**' audit trails — `negated_words`, `intensified_words`, `diminished_words`,
and `directional_words` each list the phrase that triggered that specific rule
(e.g. `not good`, `sharply declined`, `slightly improved`, `profits fell`), so
every rule's effect is separately auditable. See "Context rules" below.

Evaluate against a labeled dataset (see format below):

```
python main.py evaluate --labeled examples/labeled_sample.csv
```

This prints Accuracy, macro-averaged Precision, macro-averaged F1-score, and a
per-class breakdown.

Scan articles for candidate words to add to the supplement list (see "Building
the supplement list" below):

```
python main.py suggest-supplement --input data/input --output supplement_candidates.csv
```

List every word that matched the lexicon via its lemma rather than its exact
spelling (read-only, prints to the console — see "Match-type provenance" below
for why lemma matches are worth auditing):

```
python main.py lemma-report --input data/input
```

Each line shows `surface_word -> lemma  (weight=..., lexicon=..., frequency=...)`.
Words in `LEMMA_EXCLUDED_WORDS` (e.g. `"latest"`) never appear here, since they
can't match via lemma at all.

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

### Match-type provenance, and a real bug it caught: "latest"

Every matched word records **how** it matched, not just which lexicon it came
from — `MatchedWord.match_type` is `"exact"` or `"lemma"`, shown in the output as
the second half of the `[SOURCE:MATCH]` tag (e.g. `declining[LM:lemma]`). This
matters because lemma matches are exactly the ones prone to semantic drift: a
word's lemma can carry a different meaning than the word itself.

That's not hypothetical — it's how we found a real bug. "latest" lemmatizes to
`"late"`, which is correctly in LM's negative list (e.g. "late payment," "late
filing"), but "latest" just means "most recent" and has no sentiment of its own.
Before match-type tagging existed, this was invisible: "latest" would show up
tagged `[LM]` exactly like a real negative match, with nothing to distinguish it
from an intentional one.

The fix is `LEMMA_EXCLUDED_WORDS` in `lexicon.py`: a small, hand-editable set of
surface words that can only ever match their own exact spelling — the lemma path
is skipped for them entirely, even when the lemma would otherwise hit. It's
seeded with `"latest"`. If you spot another word whose `[…:lemma]` tag looks
wrong, add it here; its exact spelling (if it's ever a real lexicon word on its
own) still matches normally, only the lemma shortcut is disabled.
`suggest_supplement_candidates()` (the `suggest-supplement` scan) respects this
list too, since it shares the same `lookup_word()` function `SentimentAnalyzer`
uses — so an excluded word won't get suggested as a false candidate either.

## Context rules

Negation, intensifiers, and diminishers are all **context rules**: something
that adjusts a matched word's weight based on a nearby cue word, rather than
the word's own lexicon entry. They share one shape (`context_rules.py`):

```python
@dataclass(frozen=True)
class RuleEffect:
    multiplier: float   # how much to scale the matched word's weight by
    phrase: str          # the phrase for the rule's audit column, e.g. "not good"
```

Each rule module exposes a `RULE_NAME` and a
`find_effect(tokens, index, window=3) -> RuleEffect | None`. `analyzer.py` runs
every rule generically for each matched word — multiplying `weight` by every
effect found and recording `effect.phrase` in that rule's own audit column.
Adding a future rule type is one new module plus one line in `analyzer.py`'s
`CONTEXT_RULES` list; nothing else needs to change.

**Guardrail:** a context rule only ever looks at a fixed cue-word set (like
`NEGATION_WORDS`) — never at another matched sentiment word's polarity. Mixed-
sentiment sentences ("strong revenue but weak margins") are legitimate and stay
mixed; nothing here nudges one sentiment word based on another one nearby.

### Negation

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

Negation is the one context rule that's **backward-only** (it only looks at
tokens *before* the sentiment word), unlike intensifiers/diminishers/directional
words below, which look both ways. English negation cues precede what they
negate ("not good", never "good not") — checking forward too would risk
misattributing a later, unrelated negation, e.g. in "good, not bad", a forward
check could wrongly flag "good" using the "not" that actually negates "bad".

### Intensifiers

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
when one is within 3 tokens of a sentiment word (before or after), it multiplies
that word's weight by 1.5x, which shows up in `weighted_score` and the
`intensified_words` column. If more than one intensifier is nearby, only the
**closest** one applies (they don't stack) — this keeps one clean phrase per hit
for the audit column, the same way negation only uses the closest cue.

We deliberately kept this list narrow. Some similar-looking LM words were left out
because they carry their own judgment even with nothing to modify — e.g.
"excessively," "unduly," and "grossly" all imply "more than is acceptable," which
is itself a negative judgment, not just a magnitude.

### Diminishers

The mirror image of intensifiers: `diminishers.py` lists `slightly`, `somewhat`,
`modestly`, and `barely`, each with a 0.5x multiplier that **shrinks** a nearby
word's weight instead of amplifying it ("slightly higher" should count for less
than a plain "higher"). Same closest-match-only rule as intensifiers, logged in
the `diminished_words` column. Unlike the intensifier words, none of these are
LM words being reclassified — this is new coverage, not a migration.

## Directional words

Words like "rise," "fall," "climb," "decline," "drop," and "gain" carry no
sentiment of their own — whether "profits fell" is good or bad news depends
entirely on what's falling. "Profits fell" is negative; "costs fell" is
positive. A flat lexicon entry (which is what LM used to do for
"decline"/"gain," and what Harvard IV-4 does for "drop") can't express that.

`directional.py` resolves these against two small, explicit topic-noun lists:

```python
POSITIVE_TOPICS = {"profit", "profits", "revenue", "revenues", "growth",
                    "margin", "margins", "earnings", "demand", "gains"}
NEGATIVE_TOPICS = {"cost", "costs", "loss", "losses", "debt", "default",
                    "defaults", "litigation", "unemployment"}
```

The rule, searching up to 3 tokens either side of the directional word for the
closest topic noun:

| topic | direction | result |
|---|---|---|
| positive-topic | up | positive ("profits rose") |
| positive-topic | down | negative ("profits fell") |
| negative-topic | down | positive ("costs fell") |
| negative-topic | up | negative ("costs rose") |

If there's **no topic noun nearby**, the directional word contributes nothing at
all — same principle as an intensifier with nothing nearby to amplify. A
resolved directional word shows up in `positive_words`/`negative_words` tagged
`[TOPIC:exact]` (not `[LM]`/`[SUPP]`, since its weight didn't come from a
lexicon lookup), and its phrase (e.g. `profits fell`) is logged in the
`directional_words` column.

`erased`/`erase`/`erasing`/`erases` are also handled here, as a "down" (removing/
eliminating) direction — "erased losses" resolves positive (negative-topic +
down = positive), "erased gains" resolves negative. That's why `gains` is in
`POSITIVE_TOPICS`: so it can pair with `losses` (already there) as the two nouns
`erased` most commonly modifies.

### Why explicit surface forms, not lemmas

`DIRECTIONAL_WORDS` lists every inflection by hand (`rise/rises/rising/rose/
risen`, `fall/falls/falling/fell/fallen`, etc.) instead of matching a lemma the
way normal lexicon lookups do. We checked `simplemma` on exactly these words
first, and it has real gaps that would have silently broken this feature:
`rose` and `fell` — the two most common forms in headlines — don't reduce to
`rise`/`fall` at all (they lemmatize to themselves), and `dropping` doesn't
reduce to `drop` either. Relying on lemma fallback here would have missed
exactly the words real news headlines use most.

### Migrating `decline`/`gain`/`drop` off flat lexicon scoring

`analyzer.py` checks `is_directional(token)` **before** the normal lexicon
lookup, so directional words are always intercepted here regardless of what's
still sitting in the underlying LM/Harvard IV-4 data (we don't hand-edit those
vendored CSV files). Checked directly: LM had `decline`/`declines`/`declining`/
`declined` (all -1.0) and `gain`/`gains`/`gaining`/`gained` (all +1.0) as flat
entries; Harvard IV-4 separately had `drop` (-1.0, not in LM at all). All of
these are now fully handled by the topic-resolution system above instead —
`tests/test_analyzer.py::test_decline_and_gain_are_migrated_off_flat_lm_scoring`
confirms a bare "decline"/"gain" with no topic noun nearby now scores as
neutral, where it used to score flat regardless of context.
`suggest_supplement_candidates()` also excludes directional words from its
candidate list for the same reason — e.g. `drop` would otherwise resurface as a
"new" Harvard IV-4 candidate even though it's already handled.

### Known simplification, not fixed here

`surged`, `sank`, `slumped`, `plunge`, and `tumble` (all flat entries in
`supplement_lexicon.csv`) are topic-dependent the same way `decline`/`gain`
were — e.g. "inflation surged" is bad news, but a flat `surged: +1.0` scores it
positive. If evaluation ever shows errors specifically on inflation/costs/yields
articles (where "rising" is bad, unlike for profits/revenue), these are the
words to migrate into `directional.py` next.

## Where each matched word comes from (LM vs. supplement)

Every matched word's source lexicon is shown in the output as `word[LM]` or
`word[SUPP]`. `lexicon.py`'s `load_combined_lexicon()` builds this from two
**automatic** sources: LM (primary) and `supplement_lexicon.csv` (your approved
extra words). LM always wins on overlap. Harvard IV-4 is **not** one of the
automatic sources — see below for why, and "Building the supplement list" for how
it's used instead.

### Why Harvard IV-4 isn't merged in automatically

We tried this first (merging in Harvard IV-4, a general-purpose, not finance-
specific dictionary, as an automatic fallback for anything LM didn't cover) and
measured the result on 3 real news articles: **51-76% of all matched words came
from Harvard IV-4, not LM** — words like `share`, `main`, `open`, `interest`,
`war`, `cost`, and `need` all got tagged as sentiment words, which a finance-aware
reader wouldn't count. Harvard IV-4 has roughly 3,600 tagged words vs. LM's
~2,700, and general news prose uses a lot more everyday vocabulary than the
formal filing language LM was built from — so its breadth dominated by sheer word
count. In practice, `weighted_score`/`net_score` ended up driven more by generic-
English sentiment than finance-specific judgment.

So Harvard IV-4 is now used only for *suggesting* candidates — never merged in
directly. This preserves one genuinely useful piece of it: even restricted to a
word's most common sense (see `load_hiv4_lexicon()`'s docstring for the `#1`-
sense filtering logic, still used for scanning), Harvard IV-4 does catch a few
real finance-relevant words LM misses entirely (`sank`, `slump`, `surge`,
`rally`) — they just need a human to confirm they're not noise before they're
trusted, rather than being trusted automatically.

## Building the supplement list

`python main.py suggest-supplement --input data/input --output supplement_candidates.csv`
scans your articles for words that would match Harvard IV-4 but aren't already
covered by LM or your current supplement list, and writes them out as
`word, hiv4_weight, frequency`, sorted by frequency so the most impactful
candidates are easiest to review. It never edits `supplement_lexicon.csv` itself
— you copy over whichever rows you approve by hand. That file has two columns,
`word,weight`; a missing or empty file just means no supplement words, not an
error.

The starter list already in `supplement_lexicon.csv` was built this way from 3
real articles, filtered by hand down to genuinely useful, unambiguous-direction
words (`surged`, `rally`, `optimism`, `upbeat`, `rosy`, `steady`, `sank`,
`slumped`, `dumped`), plus 5 words added with no lexicon source at all (`plunge`,
`tumble`, `rout`, `routed`, `selloff` — see below for why `routed` needed its own
row). Tempting-looking candidates were deliberately left out where they're too
context-dependent to trust as a flat weight — e.g. `profit` (LM/Harvard IV-4 tag
it positive, but "profit warning" is negative), `crushed`/`ripped` (can mean
either "beat estimates" or "got hurt," depending on direction), and words that
were false positives from an unrelated sense in the source text (`artificial`
from "artificial intelligence," `fabrication` from "chip fabrication").

**Known simplification:** `surged`, `sank`, `slumped`, `plunge`, and `tumble` are
kept as flat entries even though they're technically topic-dependent too, the
same way `decline`/`gain` used to be — see "Directional words" above for the
system that now handles that class of word, and why these five weren't migrated
into it yet.

### A lemmatizer quirk worth knowing: `routed`

`simplemma` (see "How matching actually works" above) incorrectly lemmatizes
"routed" to `"route"` (a different word), not `"rout"` — so relying on lemma
fallback from a `rout` entry alone would silently miss the inflected form real
headlines actually use ("stocks were routed"). That's why `routed` has its own
explicit row in `supplement_lexicon.csv` instead of relying on the lemma path
like `plunge`/`tumble` do for their own inflections.

### Correcting an earlier mistake

An earlier summary from this project claimed "sank" doesn't match at all. That
was wrong — it was a stale leftover from before Harvard IV-4 was wired in at all,
never corrected afterward. Traced end-to-end: `sank` matches via its **exact
surface form** (no lemmatization involved — `_lookup()` tries the exact spelling
first and only falls back to a lemma on a miss, so lemma fallback can only ever
*add* matches, never shadow an existing exact one). `tests/test_analyzer.py::
test_sank_matches_via_supplement_regression` pins this down.

### Words we still can't catch, and why

`selloff` doesn't match hyphenated ("sell-off") or two-word ("sell off") spellings
— `tokenizer.py` splits on anything that isn't a letter, so those would tokenize
into separate words. Not fixed here; a known limitation of single-token matching.

More broadly, we checked VADER and SentiWordNet (in addition to Harvard IV-4)
against this class of financial-news vocabulary before deciding to hand-curate
the supplement list instead of merging in another lexicon:
- **VADER**: only `crash` is present; everything else checked is absent. VADER's
  ~7,500-word lexicon skews toward social-media/informal language.
- **SentiWordNet**: scores nearly all of these words as "objective"/neutral, even
  senses whose definitions literally say "decline markedly" or "suffer a sudden
  downfall." It's automatically derived from WordNet glosses, and physical-motion
  verbs like "sink" or "plunge" aren't inherently emotionally loaded in general
  English — their negative meaning is specific to the financial context, which is
  exactly the kind of domain nuance general lexicons don't capture (ironically,
  the same reason LM had to be built in the first place).

**Bottom line:** there's no clean off-the-shelf lexicon that fully closes this
gap — the supplement-list workflow above (scan, review, approve by hand) is the
realistic path, not a bigger automatic merge.

## Extension points already built into the code

- **Weighted scoring.** `lexicon.py` returns a `word -> LexiconEntry(weight, source)`
  dictionary (currently every word is +1.0 or -1.0) instead of two plain lists.
  `analyzer.py` already sums these weights into a `weighted_score` field. To make
  some words count more than others (e.g. "bankruptcy" = -3.0), just edit the
  weights in `lexicon.py` — `analyzer.py` and everything downstream will pick it up
  automatically.
- **Intensifier/diminisher strength.** `intensifiers.py`'s and `diminishers.py`'s
  `DEFAULT_MULTIPLIER` and per-word dicts are both easy to tune independently per
  word.
- **New context rules.** Any new rule that scales a matched word's weight based
  on a nearby cue word is one new module (`RULE_NAME` + `find_effect()`, see
  "Context rules") plus one line in `analyzer.py`'s `CONTEXT_RULES` list.
- **New topic nouns / directional words.** `directional.py`'s `POSITIVE_TOPICS`,
  `NEGATIVE_TOPICS`, and `DIRECTIONAL_WORDS` are plain sets/dicts — easy to
  extend (e.g. adding `yields` as a topic, or migrating `surged`/`sank` in from
  the supplement list, per the known simplification above).
- **Negation dampening.** Right now negation fully flips a word's sign. A more
  nuanced version (dampen the magnitude instead of a full flip, similar to how
  VADER does it) would only require changing `negation.py`'s `find_effect()` to
  return a smaller-magnitude multiplier, once weights are more than just ±1.
