"""
Shared shape for "context rules" - things that adjust a matched sentiment
word's weight based on a nearby cue word, rather than the word's own lexicon
entry. negation.py, intensifiers.py, and diminishers.py are all context
rules: each exposes a RULE_NAME constant and a
find_effect(tokens, index, window) -> RuleEffect | None function with this
same shape, so analyzer.py can run all of them generically for every matched
word - adding a new rule type is one new module plus one line in
analyzer.py's rule list, no other changes needed.

Guardrail: a context rule only ever looks at fixed cue-word sets (e.g.
NEGATION_WORDS, INTENSIFIER_WORDS) - never at another matched sentiment
word's polarity. Mixed-sentiment sentences ("strong revenue but weak
margins") are legitimate and must stay mixed; nothing here nudges one
sentiment word based on another one nearby.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleEffect:
    """One context rule's effect on a matched word."""

    multiplier: float  # how much to scale the matched word's weight by
    phrase: str  # reconstructed phrase for the rule's audit column, e.g. "not good"
