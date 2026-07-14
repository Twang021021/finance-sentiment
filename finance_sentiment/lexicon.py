"""
Loads word sentiment lexicons: the Loughran-McDonald (LM) financial word list
(primary, automatic), a small hand-approved supplement list (also automatic),
and the Harvard IV-4 General Inquirer dictionary (used only to *suggest*
supplement candidates for review — see suggest_supplement_candidates() and
main.py's `suggest-supplement` command — never merged in automatically).

We don't use pysentiment2's own analysis code (it stems words like "abandoned"
down to "abandon", which makes the output harder to read). Instead we just
borrow the CSV files that pysentiment2 already ships with, and build our own
simple word -> weight lookups from them.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

import pandas as pd
from pysentiment2.base import STATIC_PATH

from . import directional as directional_module
from . import lemmatizer as lemmatizer_module
from . import tokenizer as tokenizer_module

_LexiconValue = TypeVar("_LexiconValue")

LM_CSV_PATH = f"{STATIC_PATH}/LM.csv"
HIV4_CSV_PATH = f"{STATIC_PATH}/HIV-4.csv"
SUPPLEMENT_CSV_PATH = Path(__file__).parent / "supplement_lexicon.csv"

POSITIVE_WEIGHT = 1.0
NEGATIVE_WEIGHT = -1.0

LM_SOURCE = "LM"
HIV4_SOURCE = "HIV4"
SUPPLEMENT_SOURCE = "SUPP"

EXACT_MATCH = "exact"
LEMMA_MATCH = "lemma"

# Words that must never match through the lemma fallback, only their own
# exact spelling. Seeded with "latest": it lemmatizes to "late" (in LM's
# negative list, correctly, for things like "late payment"), but "latest"
# just means "most recent" and has no sentiment of its own. Add a word here
# whenever you spot a lemma match that changed its meaning - matches tagged
# [lemma] in the output (see analyzer.py/io_utils.py) are the ones prone to
# this, since that's exactly what this list guards against.
LEMMA_EXCLUDED_WORDS: set[str] = {"latest"}


@dataclass(frozen=True)
class LexiconEntry:
    """One lexicon lookup result: the word's weight and which lexicon it came from."""

    weight: float
    source: str  # LM_SOURCE or SUPPLEMENT_SOURCE


def load_lm_lexicon() -> dict[str, float]:
    """
    Read the LM Master Dictionary CSV and return one dict mapping each
    lowercase word to a numeric weight: +1.0 for positive words, -1.0 for
    negative words.

    Using a single weighted dict (instead of two plain sets) is what makes
    future "weighted scoring" possible without changing analyzer.py: someone
    can later edit the numbers here (or load a different lexicon file) and
    the score calculation just picks up the new weights.
    """
    data = pd.read_csv(LM_CSV_PATH)

    positive_rows = data.loc[data["Positive"] > 0, "Word"]
    negative_rows = data.loc[data["Negative"] > 0, "Word"]

    lexicon: dict[str, float] = {}
    for word in positive_rows:
        lexicon[str(word).lower()] = POSITIVE_WEIGHT
    for word in negative_rows:
        lexicon[str(word).lower()] = NEGATIVE_WEIGHT

    return lexicon


def load_supplement_lexicon() -> dict[str, float]:
    """
    Read finance_sentiment/supplement_lexicon.csv - a small, hand-curated list
    of extra words (columns: word,weight) that you've explicitly approved,
    either rescued from Harvard IV-4 via `python main.py suggest-supplement`
    or added by hand (e.g. "plunge," which isn't in any lexicon we checked).

    Unlike LM/HIV-4, this file is meant to be edited directly - add or remove
    rows as you see fit. A missing or empty file just means no supplement
    words, not an error.
    """
    if not SUPPLEMENT_CSV_PATH.exists():
        return {}

    data = pd.read_csv(SUPPLEMENT_CSV_PATH)
    if data.empty:
        return {}

    return {str(row.word).lower(): float(row.weight) for row in data.itertuples()}


def _hiv4_sense_rank(entry: str) -> int:
    """
    Harvard IV-4 numbers a word's senses by how common they are, e.g.
    "COMPANY#1" (its dominant, most frequent sense) vs. "COMPANY#2" (a
    rarer sense). An entry with no "#" has only one sense. Lower = more
    common.
    """
    if "#" not in entry:
        return 0
    try:
        return int(entry.split("#")[-1])
    except ValueError:
        return 0


def load_hiv4_lexicon() -> dict[str, float]:
    """
    Read the Harvard IV-4 General Inquirer CSV and return a word -> weight
    dict, the same shape as load_lm_lexicon().

    Harvard IV-4 is a general-purpose (not finance-specific) dictionary. On
    real news articles it turned out to supply the majority of matches when
    it was merged in automatically - including plenty of finance-neutral
    words ("share," "main," "interest") - so it's no longer merged in
    automatically. It's now used only to *suggest* candidates for the
    supplement list; see suggest_supplement_candidates() below.

    Each Harvard IV-4 word can appear as several numbered senses (e.g.
    "COMPANY#1" the business entity, "COMPANY#2" the fact of being with
    someone), and only some of those senses may carry a Positiv/Negativ tag.
    We only trust a word's most common sense (#1, or its only sense if it's
    not numbered) - e.g. "company" is skipped because its #1 sense isn't
    tagged at all, even though a rarer #2 sense happens to be tagged Positiv.
    Using anything past the #1 sense would be guessing at which meaning is
    intended.
    """
    data = pd.read_csv(HIV4_CSV_PATH, low_memory=False)
    entries = data["Entry"].astype(str)
    data["base_word"] = entries.str.split("#").str[0].str.lower()
    data["sense_rank"] = entries.apply(_hiv4_sense_rank)

    # groupby(...).first() would quietly mix values from different rows
    # (it takes the first non-null value per *column*, not the first row),
    # so we sort and take each group's first row explicitly instead.
    sorted_data = data.sort_values(["base_word", "sense_rank"], kind="stable")
    first_sense_per_word = sorted_data.groupby("base_word", as_index=True).nth(0)
    first_sense_per_word = first_sense_per_word.set_index("base_word")

    lexicon: dict[str, float] = {}
    for word, row in first_sense_per_word.iterrows():
        if pd.notna(row["Positiv"]) and pd.isna(row["Negativ"]):
            lexicon[word] = POSITIVE_WEIGHT
        elif pd.notna(row["Negativ"]) and pd.isna(row["Positiv"]):
            lexicon[word] = NEGATIVE_WEIGHT
        # word's #1 sense has no tag, or is tagged both ways: skip it

    return lexicon


def load_combined_lexicon() -> dict[str, LexiconEntry]:
    """
    Build the lexicon SentimentAnalyzer actually uses: LM plus your approved
    supplement list. LM always wins where both have an opinion about a word.
    Each entry records which lexicon it came from so that's visible in the
    output ([LM] or [SUPP]).
    """
    lm_lexicon = load_lm_lexicon()
    supplement_lexicon = load_supplement_lexicon()

    combined: dict[str, LexiconEntry] = {
        word: LexiconEntry(weight=weight, source=LM_SOURCE) for word, weight in lm_lexicon.items()
    }
    for word, weight in supplement_lexicon.items():
        if word not in combined:
            combined[word] = LexiconEntry(weight=weight, source=SUPPLEMENT_SOURCE)

    return combined


def lookup_word(
    token: str, lexicon: dict[str, _LexiconValue]
) -> tuple[_LexiconValue, str] | None:
    """
    Find `token` in `lexicon`, trying the exact spelling first and falling
    back to its lemma (base form) if that's not found. Works for any lexicon
    dict shape (plain word -> weight, or word -> LexiconEntry) since it's
    just a lookup. Shared by SentimentAnalyzer and
    suggest_supplement_candidates() so both use identical matching rules - a
    word only counts as "not covered" if neither its exact form nor its
    lemma are in the lexicon.

    Returns (value, EXACT_MATCH or LEMMA_MATCH), or None if nothing matched.
    A word in LEMMA_EXCLUDED_WORDS can only ever match its exact form - the
    lemma path is skipped for it entirely, even if the lemma would have hit.
    """
    if token in lexicon:
        return lexicon[token], EXACT_MATCH

    if token in LEMMA_EXCLUDED_WORDS:
        return None

    lemma = lemmatizer_module.lemmatize(token)
    if lemma != token and lemma in lexicon:
        return lexicon[lemma], LEMMA_MATCH

    return None


def suggest_supplement_candidates(articles: dict[str, str]) -> list[tuple[str, float, int]]:
    """
    Scan `articles` (filename -> text) for words that would match Harvard
    IV-4 but aren't already covered by LM, the current supplement list, or
    the directional-word system (see directional.py). Returns
    (word, hiv4_weight, frequency) tuples sorted by frequency (most common
    first), for `python main.py suggest-supplement` to write out for you to
    review - see load_supplement_lexicon().
    """
    lm_lexicon = load_lm_lexicon()
    supplement_lexicon = load_supplement_lexicon()
    hiv4_lexicon = load_hiv4_lexicon()

    frequencies: Counter[str] = Counter()
    weights: dict[str, float] = {}

    for text in articles.values():
        for token in tokenizer_module.tokenize(text):
            if directional_module.is_directional(token):
                continue  # handled by the directional-topic system, not a flat weight
            if lookup_word(token, lm_lexicon) is not None:
                continue  # already covered by LM
            if lookup_word(token, supplement_lexicon) is not None:
                continue  # already approved
            hiv4_match = lookup_word(token, hiv4_lexicon)
            if hiv4_match is not None:
                weight, _match_type = hiv4_match
                frequencies[token] += 1
                weights[token] = weight

    return [(word, weights[word], freq) for word, freq in frequencies.most_common()]


def find_lemma_matches(articles: dict[str, str]) -> list[tuple[str, str, float, str, int]]:
    """
    Scan `articles` (filename -> text) for every word that matched the
    combined lexicon via its LEMMA rather than its exact spelling (see
    lookup_word()). Returns (surface_word, lemma, weight, source, frequency)
    tuples sorted by frequency (most common first), for
    `python main.py lemma-report` - useful for auditing lemma-driven matches
    for semantic drift, like "latest" incorrectly matching via its lemma
    "late" (see LEMMA_EXCLUDED_WORDS). Words in LEMMA_EXCLUDED_WORDS never
    show up here, since lookup_word() refuses to match them via lemma at all.
    """
    combined_lexicon = load_combined_lexicon()

    frequencies: Counter[str] = Counter()
    details: dict[str, tuple[str, float, str]] = {}

    for text in articles.values():
        for token in tokenizer_module.tokenize(text):
            match = lookup_word(token, combined_lexicon)
            if match is None:
                continue
            entry, match_type = match
            if match_type != LEMMA_MATCH:
                continue

            frequencies[token] += 1
            details[token] = (lemmatizer_module.lemmatize(token), entry.weight, entry.source)

    return [(word, *details[word], freq) for word, freq in frequencies.most_common()]


def positive_words(lexicon: dict[str, float]) -> set[str]:
    """Words in the lexicon with a positive weight."""
    return {word for word, weight in lexicon.items() if weight > 0}


def negative_words(lexicon: dict[str, float]) -> set[str]:
    """Words in the lexicon with a negative weight."""
    return {word for word, weight in lexicon.items() if weight < 0}
