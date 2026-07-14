"""
The core sentiment analysis logic: turn one piece of text into positive/
negative word matches, counts, and two score fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import diminishers as diminishers_module
from . import directional as directional_module
from . import intensifiers as intensifiers_module
from . import negation as negation_module
from . import tokenizer as tokenizer_module
from .lexicon import LexiconEntry
from .lexicon import lookup_word as lexicon_lookup_word

# Directional words (see directional.py) don't come from a lexicon lookup -
# their weight is resolved from a nearby topic noun instead - so they get
# their own source tag rather than "LM"/"SUPP".
DIRECTIONAL_SOURCE = "TOPIC"

# Context rules run generically for every matched (non-directional) word:
# each module exposes RULE_NAME and find_effect(tokens, index) -> RuleEffect
# | None (see context_rules.py). Adding a new rule type is one new module
# plus one line here - no other changes to analyze() are needed.
CONTEXT_RULES = [negation_module, intensifiers_module, diminishers_module]


@dataclass
class MatchedWord:
    """One sentiment word found in the text."""

    word: str  # the original surface form, exactly as it appeared in the text
    source: str  # which lexicon it matched from: "LM", "SUPP", or "TOPIC" (see lexicon.py/directional.py)
    # "exact" (word spelled exactly as in the lexicon) or "lemma" (matched
    # via its base form - see lemmatizer.py). Lemma matches are the ones
    # prone to semantic drift (e.g. "latest" -> "late"), so this is worth
    # auditing separately from the source lexicon. Directional words are
    # always "exact" (they're matched by their own surface form - see
    # directional.py).
    match_type: str = "exact"


@dataclass
class AnalysisResult:
    positive_count: int
    negative_count: int
    positive_words: list[MatchedWord] = field(default_factory=list)
    negative_words: list[MatchedWord] = field(default_factory=list)
    # one audit list per context rule - phrases like "not good" (negation),
    # "sharply declined" (intensifier), "slightly improved" (diminisher), or
    # "profits fell" (directional), so each rule's effect is auditable
    negated_words: list[str] = field(default_factory=list)
    intensified_words: list[str] = field(default_factory=list)
    diminished_words: list[str] = field(default_factory=list)
    directional_words: list[str] = field(default_factory=list)
    # net_score is just positive_count - negative_count.
    net_score: int = 0
    # weighted_score sums each matched word's (possibly negated/intensified/
    # diminished) weight. Today every word starts at +1 or -1, so before
    # context rules this would equal net_score. It's a separate field so
    # that later, editing weights in lexicon.py changes this score without
    # needing any changes here.
    weighted_score: float = 0.0


class SentimentAnalyzer:
    """Analyzes text using a word -> LexiconEntry lookup (see lexicon.py)."""

    def __init__(self, lexicon: dict[str, LexiconEntry]):
        self.lexicon = lexicon

    def _lookup(self, token: str) -> tuple[LexiconEntry, str] | None:
        """
        Find a lexicon entry for `token`, trying the exact spelling first
        and falling back to its lemma (base form) if that's not found (see
        lexicon.lookup_word - shared with suggest_supplement_candidates()
        so both use identical matching rules). Returns (entry, match_type).
        """
        return lexicon_lookup_word(token, self.lexicon)

    def analyze(self, text: str) -> AnalysisResult:
        tokens = tokenizer_module.tokenize(text)

        positive_words: list[MatchedWord] = []
        negative_words: list[MatchedWord] = []
        directional_words: list[str] = []
        rule_phrases: dict[str, list[str]] = {rule.RULE_NAME: [] for rule in CONTEXT_RULES}
        weighted_score = 0.0

        for index, token in enumerate(tokens):
            # Intensifiers/diminishers ("sharply," "slightly," ...) never
            # count as their own word - they only scale a nearby sentiment
            # word below, via the CONTEXT_RULES loop.
            if intensifiers_module.is_intensifier(token) or diminishers_module.is_diminisher(token):
                continue

            # Directional words ("rose," "fell," "declined," ...) carry no
            # sentiment of their own - resolve them from a nearby topic noun
            # instead of the normal lexicon lookup, and skip that lookup
            # entirely. This is what keeps decline/gain/drop from also being
            # scored as flat LM/HIV-4 entries.
            if directional_module.is_directional(token):
                resolved = directional_module.resolve_weight(tokens, index)
                if resolved is not None:
                    weight, phrase = resolved
                    matched = MatchedWord(word=token, source=DIRECTIONAL_SOURCE)
                    if weight > 0:
                        positive_words.append(matched)
                    else:
                        negative_words.append(matched)
                    directional_words.append(phrase)
                    weighted_score += weight
                continue

            match = self._lookup(token)
            if match is None:
                continue
            entry, match_type = match

            weight = entry.weight
            for rule in CONTEXT_RULES:
                effect = rule.find_effect(tokens, index)
                if effect is not None:
                    weight *= effect.multiplier
                    rule_phrases[rule.RULE_NAME].append(effect.phrase)

            matched = MatchedWord(word=token, source=entry.source, match_type=match_type)
            if weight > 0:
                positive_words.append(matched)
            elif weight < 0:
                negative_words.append(matched)

            weighted_score += weight

        positive_count = len(positive_words)
        negative_count = len(negative_words)

        return AnalysisResult(
            positive_count=positive_count,
            negative_count=negative_count,
            positive_words=positive_words,
            negative_words=negative_words,
            negated_words=rule_phrases[negation_module.RULE_NAME],
            intensified_words=rule_phrases[intensifiers_module.RULE_NAME],
            diminished_words=rule_phrases[diminishers_module.RULE_NAME],
            directional_words=directional_words,
            net_score=positive_count - negative_count,
            weighted_score=weighted_score,
        )
