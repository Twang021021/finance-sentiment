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
net_score), and instead uses them to multiply the weight of the closest
nearby sentiment word, which shows up in weighted_score and the
intensified_words audit column.
"""

from __future__ import annotations

from .context_rules import RuleEffect

RULE_NAME = "intensifier"

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


def _find_closest_intensifier_index(tokens: list[str], index: int, window: int) -> int | None:
    """Look both before and after tokens[index] for the closest intensifier word within `window` tokens."""
    best_index = None
    best_distance = None
    start = max(0, index - window)
    end = min(len(tokens), index + window + 1)

    for i in range(start, end):
        if i == index:
            continue
        if tokens[i] in INTENSIFIER_WORDS:
            distance = abs(i - index)
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_index = i

    return best_index


def find_effect(tokens: list[str], index: int, window: int = 3) -> RuleEffect | None:
    """
    The context-rule interface used generically by analyzer.py (see
    context_rules.py): if an intensifier is nearby (e.g. "dramatically
    improved" or "improved dramatically"), return its multiplier and the
    reconstructed phrase for the intensified_words audit column. Only the
    single closest intensifier applies - not every one in range - so there's
    one clean phrase per hit.
    """
    intensifier_index = _find_closest_intensifier_index(tokens, index, window)
    if intensifier_index is None:
        return None

    multiplier = INTENSIFIER_WORDS[tokens[intensifier_index]]
    start, end = sorted((intensifier_index, index))
    phrase = " ".join(tokens[start : end + 1])
    return RuleEffect(multiplier=multiplier, phrase=phrase)
