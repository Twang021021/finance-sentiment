"""
Loads word sentiment lexicons: the Loughran-McDonald (LM) financial word
list (primary) and the Harvard IV-4 General Inquirer dictionary (fallback,
for words LM doesn't cover).

We don't use pysentiment2's own analysis code (it stems words like "abandoned"
down to "abandon", which makes the output harder to read). Instead we just
borrow the CSV files that pysentiment2 already ships with, and build our own
simple word -> weight lookups from them.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from pysentiment2.base import STATIC_PATH

LM_CSV_PATH = f"{STATIC_PATH}/LM.csv"
HIV4_CSV_PATH = f"{STATIC_PATH}/HIV-4.csv"

POSITIVE_WEIGHT = 1.0
NEGATIVE_WEIGHT = -1.0

LM_SOURCE = "LM"
HIV4_SOURCE = "HIV4"


@dataclass(frozen=True)
class LexiconEntry:
    """One lexicon lookup result: the word's weight and which lexicon it came from."""

    weight: float
    source: str  # LM_SOURCE or HIV4_SOURCE


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

    Harvard IV-4 is a general-purpose (not finance-specific) dictionary, so
    it's used only as a fallback for words LM doesn't cover — see
    load_combined_lexicon(). Each Harvard IV-4 word can appear as several
    numbered senses (e.g. "COMPANY#1" the business entity, "COMPANY#2" the
    fact of being with someone), and only some of those senses may carry a
    Positiv/Negativ tag. We only trust a word's most common sense (#1, or
    its only sense if it's not numbered) — e.g. "company" is skipped
    because its #1 sense isn't tagged at all, even though a rarer #2 sense
    happens to be tagged Positiv. Using anything past the #1 sense would be
    guessing at which meaning is intended.
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
    Build the lexicon SentimentAnalyzer actually uses: LM plus an HIV-4
    fallback for words LM doesn't have. LM always wins where both have an
    opinion about a word; HIV-4 only fills in gaps. Each entry records which
    lexicon it came from so that's visible in the output.
    """
    lm_lexicon = load_lm_lexicon()
    hiv4_lexicon = load_hiv4_lexicon()

    combined: dict[str, LexiconEntry] = {
        word: LexiconEntry(weight=weight, source=LM_SOURCE) for word, weight in lm_lexicon.items()
    }
    for word, weight in hiv4_lexicon.items():
        if word not in combined:
            combined[word] = LexiconEntry(weight=weight, source=HIV4_SOURCE)

    return combined


def positive_words(lexicon: dict[str, float]) -> set[str]:
    """Words in the lexicon with a positive weight."""
    return {word for word, weight in lexicon.items() if weight > 0}


def negative_words(lexicon: dict[str, float]) -> set[str]:
    """Words in the lexicon with a negative weight."""
    return {word for word, weight in lexicon.items() if weight < 0}