"""
Diminisher handling: the mirror image of intensifiers.py. A handful of
words are pure degree/magnitude modifiers that shrink a nearby sentiment
word's weight instead of amplifying it - "slightly" isn't good or bad by
itself, it just makes whatever it's next to less extreme ("slightly higher"
vs. "sharply higher").

DIMINISHER_WORDS aren't in LM at all today (unlike the intensifier words,
which were previously miscounted as their own LM sentiment words), so there's
no "previously counted as..." history here - this is new coverage, not a
migration.
"""

from __future__ import annotations

from .context_rules import RuleEffect

RULE_NAME = "diminisher"

DEFAULT_MULTIPLIER = 0.5

DIMINISHER_WORDS: dict[str, float] = {
    "slightly": DEFAULT_MULTIPLIER,
    "somewhat": DEFAULT_MULTIPLIER,
    "modestly": DEFAULT_MULTIPLIER,
    "barely": DEFAULT_MULTIPLIER,
}


def is_diminisher(token: str) -> bool:
    """True if `token` should be treated as a magnitude modifier, not a standalone sentiment word."""
    return token in DIMINISHER_WORDS


def _find_closest_diminisher_index(tokens: list[str], index: int, window: int) -> int | None:
    """Look both before and after tokens[index] for the closest diminisher word within `window` tokens."""
    best_index = None
    best_distance = None
    start = max(0, index - window)
    end = min(len(tokens), index + window + 1)

    for i in range(start, end):
        if i == index:
            continue
        if tokens[i] in DIMINISHER_WORDS:
            distance = abs(i - index)
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_index = i

    return best_index


def find_effect(tokens: list[str], index: int, window: int = 3) -> RuleEffect | None:
    """
    The context-rule interface used generically by analyzer.py (see
    context_rules.py): if a diminisher is nearby (e.g. "slightly improved"
    or "improved slightly"), return its multiplier and the reconstructed
    phrase for the diminished_words audit column. Only the single closest
    diminisher applies, same as intensifiers.py.
    """
    diminisher_index = _find_closest_diminisher_index(tokens, index, window)
    if diminisher_index is None:
        return None

    multiplier = DIMINISHER_WORDS[tokens[diminisher_index]]
    start, end = sorted((diminisher_index, index))
    phrase = " ".join(tokens[start : end + 1])
    return RuleEffect(multiplier=multiplier, phrase=phrase)
