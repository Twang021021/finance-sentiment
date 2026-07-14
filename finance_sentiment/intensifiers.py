"""
Intensifier handling: a handful of words in the LM lexicon are pure
degree/magnitude modifiers ("sharply," "greatly") rather than words that
carry sentiment on their own. "Sharply" isn't good or bad by itself — it just
makes whatever it's next to more extreme ("sharply higher" vs. "sharply
lower"). Counting it as its own negative word (which the LM list otherwise
implies) double-counts sentiment and miscategorizes phrases like "sharply
higher" as negative overall.

INTENSIFIER_WORDS lists the LM words we identified as pure degree/magnitude
modifiers (no inherent positive/negative meaning of their own), each mapped
to a multiplier. We picked a deliberately narrow, unambiguous set: these six
describe *how much*, not *good or bad*. We left out LM words that are
similar-looking but carry their own judgment even without something to
modify (e.g. "excessively," "unduly," "grossly" — these imply "more than is
acceptable," which is itself a negative judgment, not just a magnitude).

Analyzer.py skips these words entirely when matching against the lexicon
(they never appear in positive_words/negative_words or count toward
net_score), and instead uses them to multiply the weight of a nearby
sentiment word, which shows up in weighted_score.
"""

from __future__ import annotations

DEFAULT_MULTIPLIER = 1.5

INTENSIFIER_WORDS: dict[str, float] = {
    # previously counted as their own negative word in lexicon.py's LM list
    "sharply": DEFAULT_MULTIPLIER,
    "severely": DEFAULT_MULTIPLIER,
    "drastically": DEFAULT_MULTIPLIER,
    # previously counted as their own positive word in lexicon.py's LM list
    "greatly": DEFAULT_MULTIPLIER,
    "tremendously": DEFAULT_MULTIPLIER,
    "exceptionally": DEFAULT_MULTIPLIER,
}


def is_intensifier(token: str) -> bool:
    """True if `token` should be treated as a magnitude modifier, not a standalone sentiment word."""
    return token in INTENSIFIER_WORDS


def adjacent_multiplier(tokens: list[str], index: int, window: int = 2) -> float:
    """
    Combine the multipliers of any intensifier words within `window` tokens
    before or after `tokens[index]` (e.g. "dramatically improved" or
    "improved dramatically"). Returns 1.0 (no change) if none are nearby.
    """
    multiplier = 1.0
    start = max(0, index - window)
    end = min(len(tokens), index + window + 1)

    for i in range(start, end):
        if i == index:
            continue
        factor = INTENSIFIER_WORDS.get(tokens[i])
        if factor is not None:
            multiplier *= factor

    return multiplier