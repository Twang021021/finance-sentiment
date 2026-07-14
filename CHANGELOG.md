# Changelog

A running history of major changes to this project, newest first. See
`CLAUDE.md` for how everything currently works and why.

## Generalized context-rule engine

- Unified negation/intensifiers behind a shared `RuleEffect` shape
  (`context_rules.py`) so each rule is one small module plugged into one
  generic loop in `analyzer.py` — each with its own CSV audit column.
- Added **diminishers** (`slightly`, `somewhat`, `modestly`, `barely` — shrink
  a nearby word's weight by 0.5x, the mirror image of intensifiers).
- Added **directional words** (`directional.py`): `rise/fall/climb/decline/
  drop/gain/erase` carry no sentiment on their own — resolved from a nearby
  topic noun instead ("profits fell" is negative, "costs fell" is positive).
  This migrated `decline`/`gain`/`drop` off flat LM/HIV-4 scoring entirely, and
  `suggest-supplement` now excludes directional words from its candidate list.

## Match-type provenance + lemma auditing

- Every matched word is now tagged `[SOURCE:MATCH]` — e.g.
  `declining[LM:lemma]` — exposing *how* it matched, not just from where.
- This caught a real bug: `"latest"` was matching via its lemma `"late"`
  (correctly negative for "late payment," wrong for "latest earnings"). Fixed
  with `LEMMA_EXCLUDED_WORDS`, an editable list of words barred from the lemma
  path.
- Added `lemma-report`: audits every lemma-driven match across a set of
  articles.

## Lexicon layer fix: HIV-4 becomes opt-in

- Measured that HIV-4-as-automatic-fallback was supplying **51-76% of all
  matches** on real articles, including neutral words like `share`/
  `interest`/`cost` — too noisy.
- Turned it into **scan-and-approve**: `suggest-supplement` lists HIV-4
  candidates for manual review; only words explicitly copied into
  `supplement_lexicon.csv` are used automatically (tagged `[SUPP]`).
- Resolved a factual discrepancy: confirmed `"sank"` *does* match (exact-form
  match on the approved supplement word) — an earlier claim otherwise was a
  stale, uncorrected error.

## First enhancement round

- **Lemmatization** (`simplemma`): inflected forms (`declining`) match via
  their base form (`decline`) as a fallback, but the *original* word is
  always what's reported.
- **Negation**: a cue word (`not`, `never`, ...) within 3 tokens before a
  sentiment word **flips** its polarity, logged in `negated_words`.
- **Intensifiers**: `sharply`/`greatly`/etc. stopped being scored as their
  own words and instead amplify a nearby word's weight (1.5x).
- **Harvard IV-4** added as an automatic fallback for words LM missed (later
  reversed — see "Lexicon layer fix" above).

## GitHub + repo hygiene

- Initialized git, published as a private GitHub repo.
- Added `.gitignore` for `venv/`, `results.csv`, and `data/input/` (real news
  articles are often copyrighted, so that folder stays local-only), with
  `examples/sample_articles/` as a safe-to-commit stand-in.

## Initial build

A lexicon-based sentiment tool: tokenizes finance articles, looks up each
word against the **Loughran-McDonald (LM)** financial word list (via
`pysentiment2`, read directly rather than through its stemming API so
matches stay exact and interpretable). Outputs positive/negative word counts,
the actual matched words, and net/weighted scores per article. Added an
`evaluate` command (Accuracy/Precision/F1 against a labeled CSV) and a
beginner-focused `CLAUDE.md`.
