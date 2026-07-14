"""
Directional-word handling: words like "rise," "fall," "decline," and "gain"
carry no sentiment of their own - whether "profits fell" is good or bad news
depends entirely on what's falling. "Profits fell" is negative; "costs fell"
is positive. A flat lexicon entry (which is what LM/HIV-4 do today for
"decline"/"gain"/"drop" - see lexicon.py) can't express that.

DIRECTIONAL_WORDS lists explicit surface forms (not lemmas) mapped to "up" or
"down". We use explicit forms rather than lemmatizing on the fly because
`simplemma` doesn't reliably reduce these to a common base - notably "rose"
and "fell" (extremely common in headlines) stay as themselves rather than
reducing to "rise"/"fall", and "dropping" stays as itself too. Relying on
lemma fallback here would silently miss exactly the forms real headlines use.

analyzer.py checks is_directional(token) *before* the normal lexicon lookup,
so these words are always handled here - this is what "migrates"
decline/gain/drop away from being flat LM/HIV-4 entries, without needing to
edit those vendored CSV files.

POSITIVE_TOPICS / NEGATIVE_TOPICS are the small, explicit noun lists a
directional word's polarity gets resolved against. Also matched as literal
surface forms rather than lemmas, for the same reliability reason.

Known simplification, not addressed here: "surged," "sank," "slumped,"
"plunge," and "tumble" (in supplement_lexicon.csv) are topic-dependent the
same way "decline"/"gain" are - e.g. "inflation surged" is bad news, but
they're kept as flat entries rather than migrated to this system. See
CLAUDE.md.
"""

from __future__ import annotations

UP = "up"
DOWN = "down"

DIRECTIONAL_WORDS: dict[str, str] = {
    "rise": UP,
    "rises": UP,
    "rising": UP,
    "rose": UP,
    "risen": UP,
    "fall": DOWN,
    "falls": DOWN,
    "falling": DOWN,
    "fell": DOWN,
    "fallen": DOWN,
    "climb": UP,
    "climbs": UP,
    "climbing": UP,
    "climbed": UP,
    "decline": DOWN,
    "declines": DOWN,
    "declining": DOWN,
    "declined": DOWN,
    "drop": DOWN,
    "drops": DOWN,
    "dropping": DOWN,
    "dropped": DOWN,
    "gain": UP,
    "gains": UP,
    "gaining": UP,
    "gained": UP,
    # "erased" removes/eliminates whatever follows - treated as "down" the
    # same way "drop" is (see resolve() below for how this combines with
    # POSITIVE_TOPICS/NEGATIVE_TOPICS: "erased losses" -> positive)
    "erase": DOWN,
    "erases": DOWN,
    "erasing": DOWN,
    "erased": DOWN,
}

POSITIVE_TOPICS = {
    "profit",
    "profits",
    "revenue",
    "revenues",
    "growth",
    "margin",
    "margins",
    "earnings",
    "demand",
    "gains",
}

NEGATIVE_TOPICS = {
    "cost",
    "costs",
    "loss",
    "losses",
    "debt",
    "default",
    "defaults",
    "litigation",
    "unemployment",
}


def is_directional(token: str) -> bool:
    """True if `token` should be treated as a directional word, resolved via a nearby topic noun."""
    return token in DIRECTIONAL_WORDS


def _find_closest_topic(tokens: list[str], index: int, window: int) -> tuple[int, str] | None:
    """
    Look both before and after tokens[index] for the closest topic noun
    (from POSITIVE_TOPICS or NEGATIVE_TOPICS) within `window` tokens.
    Returns (its index, "positive" or "negative"), or None. Ties (a positive
    and a negative topic equally close) favor whichever appears first
    (lower token index) - a rare case, not expected to matter in practice.
    """
    best_index = None
    best_topic_kind = None
    best_distance = None
    start = max(0, index - window)
    end = min(len(tokens), index + window + 1)

    for i in range(start, end):
        if i == index:
            continue
        if tokens[i] in POSITIVE_TOPICS:
            topic_kind = "positive"
        elif tokens[i] in NEGATIVE_TOPICS:
            topic_kind = "negative"
        else:
            continue

        distance = abs(i - index)
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_index = i
            best_topic_kind = topic_kind

    if best_index is None:
        return None
    return best_index, best_topic_kind


def resolve_weight(tokens: list[str], index: int, window: int = 3) -> tuple[float, str] | None:
    """
    Resolve the sentiment of the directional word at tokens[index] using a
    nearby topic noun:
      positive-topic + up   -> positive   ("profits rose")
      positive-topic + down -> negative   ("profits fell")
      negative-topic + down -> positive   ("costs fell")
      negative-topic + up   -> negative   ("costs rose")
    Returns (weight, phrase) for the matched sentiment, or None if there's no
    topic noun nearby - a directional word with nothing to resolve against
    contributes no sentiment at all, the same principle as an intensifier
    with nothing nearby to amplify.
    """
    direction = DIRECTIONAL_WORDS.get(tokens[index])
    if direction is None:
        return None

    topic_match = _find_closest_topic(tokens, index, window)
    if topic_match is None:
        return None
    topic_index, topic_kind = topic_match

    is_positive_outcome = (topic_kind == "positive") == (direction == UP)
    weight = 1.0 if is_positive_outcome else -1.0

    start, end = sorted((topic_index, index))
    phrase = " ".join(tokens[start : end + 1])
    return weight, phrase
