"""
The core sentiment analysis logic: turn one piece of text into positive/
negative word counts and lists, plus two score fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import negation as negation_module
from . import tokenizer as tokenizer_module


@dataclass
class AnalysisResult:
    positive_count: int
    negative_count: int
    positive_words: list[str] = field(default_factory=list)
    negative_words: list[str] = field(default_factory=list)
    # net_score is just positive_count - negative_count.
    net_score: int = 0
    # weighted_score sums each matched word's weight from the lexicon.
    # Today every word is worth +1 or -1, so this equals net_score. It's a
    # separate field so that later, editing weights in lexicon.py changes
    # this score without needing any changes here.
    weighted_score: float = 0.0


class SentimentAnalyzer:
    """Analyzes text using a word -> weight lexicon (see lexicon.py)."""

    def __init__(self, lexicon: dict[str, float]):
        self.lexicon = lexicon

    def analyze(self, text: str) -> AnalysisResult:
        tokens = tokenizer_module.tokenize(text)

        positive_words: list[str] = []
        negative_words: list[str] = []
        weighted_score = 0.0

        for index, token in enumerate(tokens):
            weight = self.lexicon.get(token)
            if weight is None:
                continue

            # negation.is_negated always returns False for now, so this
            # has no effect yet. It's the hook for a future negation
            # feature to flip "good" to negative after seeing "not".
            if negation_module.is_negated(tokens, index):
                weight = -weight

            if weight > 0:
                positive_words.append(token)
            elif weight < 0:
                negative_words.append(token)

            weighted_score += weight

        positive_count = len(positive_words)
        negative_count = len(negative_words)

        return AnalysisResult(
            positive_count=positive_count,
            negative_count=negative_count,
            positive_words=positive_words,
            negative_words=negative_words,
            net_score=positive_count - negative_count,
            weighted_score=weighted_score,
        )
