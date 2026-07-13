from finance_sentiment.lexicon import load_lm_lexicon, negative_words, positive_words


def test_lexicon_loads_and_is_not_empty():
    lexicon = load_lm_lexicon()
    assert len(lexicon) > 1000


def test_known_positive_and_negative_words():
    lexicon = load_lm_lexicon()
    assert lexicon["profitable"] > 0
    assert lexicon["strong"] > 0
    assert lexicon["bankruptcy"] < 0
    assert lexicon["losses"] < 0


def test_positive_and_negative_word_helpers():
    lexicon = load_lm_lexicon()
    pos = positive_words(lexicon)
    neg = negative_words(lexicon)

    assert "profitable" in pos
    assert "bankruptcy" in neg
    # a word can't be in both sets
    assert pos.isdisjoint(neg)
