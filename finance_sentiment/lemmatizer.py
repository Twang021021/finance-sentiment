"""
Reduces a word to its dictionary base form (its "lemma") so inflected forms
still match the lexicon even when the exact spelling isn't a separate lexicon
entry — e.g. "declining" -> "decline".

We use the `simplemma` library instead of NLTK's WordNetLemmatizer or spaCy:
it ships its lookup data with the pip package (no separate multi-megabyte
corpus download the first time you run the tool, unlike NLTK's wordnet
corpus), it's pure Python with no heavy pipeline to load (unlike spaCy, which
needs a full trained model just for this one job), and it correctly handles
irregular forms like "sank" -> "sink" out of the box.

Note: lemmatization is only used to decide whether a word MATCHES the
lexicon. The original surface word (e.g. "declining") is always what gets
reported back to you — see analyzer.py.
"""

from __future__ import annotations

import simplemma


def lemmatize(word: str) -> str:
    """Return the base/dictionary form of `word`."""
    return simplemma.lemmatize(word, lang="en")