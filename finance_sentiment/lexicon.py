"""
Loads the Loughran-McDonald (LM) financial sentiment word list.

We don't use pysentiment2's own analysis code (it stems words like "abandoned"
down to "abandon", which makes the output harder to read). Instead we just
borrow the CSV file that pysentiment2 already ships with, and build our own
simple word -> weight lookup from it.
"""

from __future__ import annotations

import pandas as pd
from pysentiment2.base import STATIC_PATH

LM_CSV_PATH = f"{STATIC_PATH}/LM.csv"

POSITIVE_WEIGHT = 1.0
NEGATIVE_WEIGHT = -1.0


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


def positive_words(lexicon: dict[str, float]) -> set[str]:
    """Words in the lexicon with a positive weight."""
    return {word for word, weight in lexicon.items() if weight > 0}


def negative_words(lexicon: dict[str, float]) -> set[str]:
    """Words in the lexicon with a negative weight."""
    return {word for word, weight in lexicon.items() if weight < 0}
