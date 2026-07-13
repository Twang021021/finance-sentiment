"""
Turns raw article text into a list of lowercase words.

Kept deliberately simple: no stemming, no stopword removal. That way a
word in the output is always spelled exactly the way it appeared in the
lexicon and in the article, which is easier to reason about than a
stemmed/normalized form.
"""

from __future__ import annotations

import re

WORD_PATTERN = re.compile(r"[a-zA-Z']+")


def tokenize(text: str) -> list[str]:
    """Split text into lowercase word tokens."""
    return [match.lower() for match in WORD_PATTERN.findall(text)]
