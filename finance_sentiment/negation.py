"""
Negation handling — NOT IMPLEMENTED YET.

This module is an intentional placeholder / extension point. Right now
`is_negated` always returns False, so analyzer.py behaves as if negation
doesn't exist. The words and function signature are already here so that a
future version can flip a word's effect when it's preceded by a word like
"not" or "never" (e.g. "not good" should stop counting "good" as positive)
without having to change any other file.
"""

from __future__ import annotations

NEGATION_WORDS = {
    "not",
    "no",
    "never",
    "none",
    "without",
    "hardly",
    "neither",
    "nor",
    "cannot",
    "n't",
}


def is_negated(tokens: list[str], index: int, window: int = 3) -> bool:
    """
    Should the token at `tokens[index]` be treated as negated?

    Currently always returns False (negation handling is not implemented
    yet). `tokens`, `index`, and `window` are accepted now so the calling
    code in analyzer.py already has the wiring in place; a future
    implementation would look at `tokens[index - window : index]` for a
    word in NEGATION_WORDS.
    """
    return False
