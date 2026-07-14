"""
Negation handling: if a sentiment word is preceded within a few words by a
negation cue ("not", "no", "never", ...), its polarity gets flipped rather
than just ignored.

Why flip instead of suppress (zero out)? "Not good" reads to a person as
leaning negative, not as neutral — suppressing would throw that signal away
entirely. Flipping is the standard simple heuristic used in rule-based
sentiment systems (e.g. it's the basis for the sign change VADER's negation
handling applies). It's not perfect — "not terrible" doesn't really mean
"great" the way flipping implies — but with a lexicon that only has +1/-1
weights (not a continuous scale), flip-the-sign is the simplest rule that
still captures the right general direction. A more nuanced dampened-flip
(shrink the magnitude instead of fully reversing it) would be a natural
next step once weighted_score weights are more than just ±1.
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


def find_negation_cue_index(tokens: list[str], index: int, window: int = 3) -> int | None:
    """
    Look backward from `tokens[index]` for a negation cue within `window`
    tokens before it. Returns the index of the closest cue found (so the
    caller can reconstruct the full negated phrase), or None if there isn't
    one nearby.
    """
    start = max(0, index - window)
    for i in range(index - 1, start - 1, -1):
        if tokens[i] in NEGATION_WORDS:
            return i
    return None