"""
The core sentiment analysis logic: turn one piece of text into positive/
negative word matches, counts, and two score fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import intensifiers as intensifiers_module
from . import lemmatizer as lemmatizer_module
from . import negation as negation_module
from . import tokenizer as tokenizer_module
from .lexicon import LexiconEntry


@dataclass
class MatchedWord:
    """One sentiment word found in the text."""

    word: str  # the original surface form, exactly as it appeared in the text
    source: str  # which lexicon it matched from: "LM" or "HIV4" (see lexicon.py)


@dataclass
class AnalysisResult:
    positive_count: int
    negative_count: int
    positive_words: list[MatchedWord] = field(default_factory=list)
    negative_words: list[MatchedWord] = field(default_factory=list)
    # phrases like "not good" that had their polarity flipped by negation.py,
    # kept separately so they're easy to audit
    negated_words: list[str] = field(default_factory=list)
    # net_score is just positive_count - negative_count.
    net_score: int = 0
    # weighted_score sums each matched word's (possibly negated/intensified)
    # weight. Today every word starts at +1 or -1, so before negation/
    # intensifiers this would equal net_score. It's a separate field so that
    # later, editing weights in lexicon.py changes this score without
    # needing any changes here.
    weighted_score: float = 0.0


class SentimentAnalyzer:
    """Analyzes text using a word -> LexiconEntry lookup (see lexicon.py)."""

    def __init__(self, lexicon: dict[str, LexiconEntry]):
        self.lexicon = lexicon

    def _lookup(self, token: str) -> LexiconEntry | None:
        """
        Find a lexicon entry for `token`, trying the exact spelling first
        and falling back to its lemma (base form) if that's not found.
        Trying the exact spelling first means words the lexicon already
        lists directly (which is most of them - see CLAUDE.md) behave
        exactly as before; the lemma is only a fallback for less common
        inflections.
        """
        entry = self.lexicon.get(token)
        if entry is not None:
            return entry

        lemma = lemmatizer_module.lemmatize(token)
        if lemma != token:
            return self.lexicon.get(lemma)

        return None

    def analyze(self, text: str) -> AnalysisResult:
        tokens = tokenizer_module.tokenize(text)

        positive_words: list[MatchedWord] = []
        negative_words: list[MatchedWord] = []
        negated_words: list[str] = []
        weighted_score = 0.0

        for index, token in enumerate(tokens):
            # Intensifiers ("sharply," "greatly," ...) never count as their
            # own word - they only amplify a nearby sentiment word below.
            if intensifiers_module.is_intensifier(token):
                continue

            entry = self._lookup(token)
            if entry is None:
                continue

            weight = entry.weight

            cue_index = negation_module.find_negation_cue_index(tokens, index)
            if cue_index is not None:
                weight = -weight

            weight *= intensifiers_module.adjacent_multiplier(tokens, index)

            matched = MatchedWord(word=token, source=entry.source)
            if weight > 0:
                positive_words.append(matched)
            elif weight < 0:
                negative_words.append(matched)

            if cue_index is not None:
                negated_words.append(" ".join(tokens[cue_index : index + 1]))

            weighted_score += weight

        positive_count = len(positive_words)
        negative_count = len(negative_words)

        return AnalysisResult(
            positive_count=positive_count,
            negative_count=negative_count,
            positive_words=positive_words,
            negative_words=negative_words,
            negated_words=negated_words,
            net_score=positive_count - negative_count,
            weighted_score=weighted_score,
        )