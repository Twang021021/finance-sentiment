from finance_sentiment.lexicon import (
    load_combined_lexicon,
    load_hiv4_lexicon,
    load_lm_lexicon,
    negative_words,
    positive_words,
)


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


def test_hiv4_lexicon_loads_and_is_not_empty():
    lexicon = load_hiv4_lexicon()
    assert len(lexicon) > 1000


def test_hiv4_covers_words_lm_misses():
    lm = load_lm_lexicon()
    hiv4 = load_hiv4_lexicon()

    # these market-movement words aren't in LM at all (confirmed directly)
    for word in ("surge", "rally", "sank", "slump"):
        assert word not in lm

    assert hiv4["surge"] > 0
    assert hiv4["rally"] > 0
    assert hiv4["sank"] < 0
    assert hiv4["slump"] < 0


def test_hiv4_skips_words_whose_dominant_sense_is_untagged():
    hiv4 = load_hiv4_lexicon()
    # "company"'s dominant (#1) sense isn't tagged pos/neg in Harvard IV-4 -
    # only a much rarer sense is - so it must not show up here.
    assert "company" not in hiv4


def test_combined_lexicon_prefers_lm_over_hiv4():
    lm = load_lm_lexicon()
    combined = load_combined_lexicon()

    # any word LM has an opinion on keeps LM's source, even if HIV-4 also
    # tags it
    for word, weight in lm.items():
        entry = combined[word]
        assert entry.source == "LM"
        assert entry.weight == weight


def test_combined_lexicon_fills_gaps_from_hiv4():
    combined = load_combined_lexicon()

    entry = combined["surge"]
    assert entry.source == "HIV4"
    assert entry.weight > 0
