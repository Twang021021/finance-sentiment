from finance_sentiment.lexicon import (
    find_lemma_matches,
    load_combined_lexicon,
    load_hiv4_lexicon,
    load_lm_lexicon,
    load_supplement_lexicon,
    lookup_word,
    negative_words,
    positive_words,
    suggest_supplement_candidates,
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


def test_supplement_lexicon_loads_the_starter_words():
    supplement = load_supplement_lexicon()
    assert supplement["sank"] < 0
    assert supplement["surged"] > 0
    assert supplement["plunge"] < 0
    # "routed" is its own row, not relying on lemma fallback from "rout"
    # (simplemma incorrectly lemmatizes "routed" to "route")
    assert supplement["routed"] < 0


def test_combined_lexicon_prefers_lm_over_hiv4():
    lm = load_lm_lexicon()
    combined = load_combined_lexicon()

    # any word LM has an opinion on keeps LM's source
    for word, weight in lm.items():
        entry = combined[word]
        assert entry.source == "LM"
        assert entry.weight == weight


def test_combined_lexicon_no_longer_auto_merges_hiv4():
    combined = load_combined_lexicon()
    # "surge" is HIV-4-only and NOT in the approved supplement list (only
    # "surged" is) - it must not silently appear in the automatic lexicon.
    assert "surge" not in combined


def test_combined_lexicon_includes_approved_supplement_words():
    combined = load_combined_lexicon()

    entry = combined["sank"]
    assert entry.source == "SUPP"
    assert entry.weight < 0


def test_lookup_word_tries_exact_then_lemma():
    lexicon = {"decline": -1.0}
    assert lookup_word("decline", lexicon) == (-1.0, "exact")
    assert lookup_word("declining", lexicon) == (-1.0, "lemma")
    assert lookup_word("unrelated", lexicon) is None


def test_lookup_word_respects_lemma_exclusion_list():
    # "latest" lemmatizes to "late", which is a real LM-negative word (e.g.
    # "late payment") - but "latest" itself just means "most recent" and
    # must never match through that lemma path.
    lexicon = {"late": -1.0}
    assert lookup_word("latest", lexicon) is None
    # the excluded word can still match its own exact spelling
    lexicon_with_latest = {"late": -1.0, "latest": 1.0}
    assert lookup_word("latest", lexicon_with_latest) == (1.0, "exact")


def test_suggest_supplement_candidates_skips_lm_and_supplement_words():
    articles = {"a.txt": "The results were profitable and strong. The stock sank."}
    candidates = suggest_supplement_candidates(articles)
    candidate_words = {word for word, _, _ in candidates}

    # "profitable"/"strong" are LM words, "sank" is already an approved
    # supplement word - none of these should be reported as new candidates
    assert "profitable" not in candidate_words
    assert "strong" not in candidate_words
    assert "sank" not in candidate_words


def test_suggest_supplement_candidates_finds_and_counts_hiv4_only_words():
    # "surge" (unlike "surged") is HIV-4-only: not in LM, and not its own
    # exact row in the supplement list (only "surged" is, and "surge" isn't
    # reachable from it via lemma fallback the other way around).
    articles = {"a.txt": "The market saw a surge. A second surge followed."}
    candidates = suggest_supplement_candidates(articles)
    candidate_words = {word: (weight, freq) for word, weight, freq in candidates}

    assert candidate_words["surge"] == (1.0, 2)


def test_suggest_supplement_candidates_reachable_via_lemma_are_excluded():
    articles = {"a.txt": "Shares rallied. Analysts rallied behind the stock too."}
    candidates = suggest_supplement_candidates(articles)
    candidate_words = {word for word, _, _ in candidates}

    # "rally" is in the supplement list, and "rallied" reaches it via lemma
    # fallback, so "rallied" should NOT show up as a new candidate.
    assert "rallied" not in candidate_words


def test_suggest_supplement_candidates_excludes_directional_words():
    # "drop" is tagged in Harvard IV-4 (-1.0) but not in LM, so it would have
    # been reported as a candidate before directional words were excluded -
    # it's now handled by the directional-topic system instead (see
    # directional.py), not a flat weight.
    articles = {"a.txt": "Sales continued to drop throughout the quarter."}
    candidates = suggest_supplement_candidates(articles)
    candidate_words = {word for word, _, _ in candidates}

    assert "drop" not in candidate_words


def test_find_lemma_matches_finds_and_counts_lemma_only_matches():
    # "rallied" isn't its own row in supplement_lexicon.csv (only "rally" is),
    # so it reaches the lexicon via lemma fallback, not an exact match.
    articles = {"a.txt": "Shares rallied. Analysts rallied behind the stock too."}
    matches = find_lemma_matches(articles)
    match_by_word = {word: (lemma, weight, source, freq) for word, lemma, weight, source, freq in matches}

    assert match_by_word["rallied"] == ("rally", 1.0, "SUPP", 2)


def test_find_lemma_matches_excludes_exact_matches():
    articles = {"a.txt": "The results were profitable."}
    matches = find_lemma_matches(articles)
    words = {word for word, *_ in matches}

    # "profitable" matches LM exactly - it must not show up in a lemma-only report
    assert "profitable" not in words


def test_find_lemma_matches_never_includes_excluded_words():
    # "latest" would lemmatize to "late" (LM-negative) but is seeded in
    # LEMMA_EXCLUDED_WORDS, so lookup_word() never lets it match via lemma -
    # meaning it can never appear in a lemma-match report either.
    articles = {"a.txt": "The latest earnings report was released today."}
    matches = find_lemma_matches(articles)
    words = {word for word, *_ in matches}

    assert "latest" not in words
