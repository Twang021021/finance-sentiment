from finance_sentiment.analyzer import SentimentAnalyzer
from finance_sentiment.lexicon import LexiconEntry, load_combined_lexicon

TEST_LEXICON = {
    "profitable": LexiconEntry(1.0, "LM"),
    "strong": LexiconEntry(1.0, "LM"),
    "bankruptcy": LexiconEntry(-1.0, "LM"),
    "losses": LexiconEntry(-1.0, "LM"),
    "weaken": LexiconEntry(-1.0, "LM"),
    "surge": LexiconEntry(1.0, "SUPP"),
    "good": LexiconEntry(1.0, "LM"),
    "late": LexiconEntry(-1.0, "LM"),
}


def words(matches):
    """Pull just the surface word out of a list of MatchedWord for easy asserting."""
    return [match.word for match in matches]


def test_analyze_counts_and_words():
    analyzer = SentimentAnalyzer(TEST_LEXICON)
    result = analyzer.analyze("The company is profitable and strong despite some losses.")

    assert result.positive_count == 2
    assert result.negative_count == 1
    assert words(result.positive_words) == ["profitable", "strong"]
    assert words(result.negative_words) == ["losses"]
    assert result.net_score == 1
    assert result.weighted_score == 1.0


def test_analyze_with_no_matches():
    analyzer = SentimentAnalyzer(TEST_LEXICON)
    result = analyzer.analyze("The board will meet on Tuesday.")

    assert result.positive_count == 0
    assert result.negative_count == 0
    assert result.net_score == 0
    assert result.weighted_score == 0.0


def test_analyze_is_case_insensitive():
    analyzer = SentimentAnalyzer(TEST_LEXICON)
    result = analyzer.analyze("PROFITABLE and Strong results, but BANKRUPTCY looms.")

    assert result.positive_count == 2
    assert result.negative_count == 1


def test_matched_words_report_their_lexicon_source():
    analyzer = SentimentAnalyzer(TEST_LEXICON)
    result = analyzer.analyze("The stock surged as the company stayed profitable.")

    sources = {match.word: match.source for match in result.positive_words}
    assert sources["surged"] == "SUPP"
    assert sources["profitable"] == "LM"


def test_sank_matches_via_supplement_regression():
    """
    Regression test: "sank" is in the approved supplement list (added from
    Harvard IV-4 - see supplement_lexicon.csv) and must match via its exact
    surface form. This pins down a specific earlier confusion: lemma fallback
    only ever ADDS matches on top of an exact-match hit, it can never shadow
    or lose one, since SentimentAnalyzer._lookup() tries the exact spelling
    first and only falls back to the lemma if that misses.
    """
    analyzer = SentimentAnalyzer(load_combined_lexicon())
    result = analyzer.analyze("The stock sank after the announcement.")

    assert result.negative_count == 1
    sources = {match.word: match.source for match in result.negative_words}
    assert sources["sank"] == "SUPP"


def test_lemmatization_matches_inflected_forms_but_reports_surface_word():
    analyzer = SentimentAnalyzer(TEST_LEXICON)
    # "weakening" isn't in TEST_LEXICON directly, only its lemma "weaken" is.
    result = analyzer.analyze("Margins were weakening this quarter.")

    assert result.negative_count == 1
    # the reported word is the surface form actually seen in the text...
    assert words(result.negative_words) == ["weakening"]
    # ...not the lemma used to find the match.
    assert "weaken" not in words(result.negative_words)


def test_matched_words_report_exact_vs_lemma_match_type():
    analyzer = SentimentAnalyzer(TEST_LEXICON)
    result = analyzer.analyze("The bank was weakening, but margins stayed strong.")

    match_types = {match.word: match.match_type for match in result.negative_words + result.positive_words}
    assert match_types["weakening"] == "lemma"
    assert match_types["strong"] == "exact"


def test_latest_does_not_match_via_lemma_exclusion():
    """
    "latest" lemmatizes to "late" (in TEST_LEXICON as negative, same as real
    LM), but "latest" just means "most recent" and has no sentiment - it's
    seeded in LEMMA_EXCLUDED_WORDS so this lemma match never happens.
    """
    analyzer = SentimentAnalyzer(TEST_LEXICON)
    result = analyzer.analyze("The latest earnings report showed strong growth.")

    assert result.negative_count == 0
    assert "latest" not in words(result.positive_words) + words(result.negative_words)


def test_late_still_matches_normally():
    analyzer = SentimentAnalyzer(TEST_LEXICON)
    result = analyzer.analyze("The payment was late.")

    assert result.negative_count == 1
    assert words(result.negative_words) == ["late"]


def test_negation_flips_polarity_and_is_reported():
    analyzer = SentimentAnalyzer(TEST_LEXICON)
    result = analyzer.analyze("The results were not good this quarter.")

    assert result.positive_count == 0
    assert result.negative_count == 1
    assert words(result.negative_words) == ["good"]
    assert result.negated_words == ["not good"]


def test_negation_outside_window_has_no_effect():
    analyzer = SentimentAnalyzer(TEST_LEXICON)
    # "not" is 4 words before "good" (beyond the default window of 3), and
    # a fresh clause separates them, so this should NOT be treated as negated.
    result = analyzer.analyze("It is not the case that the year end was good.")

    assert result.positive_count == 1
    assert result.negative_count == 0
    assert result.negated_words == []


def test_intensifier_does_not_count_as_its_own_word():
    analyzer = SentimentAnalyzer(TEST_LEXICON)
    result = analyzer.analyze("Losses mounted sharply this year.")

    # "sharply" must not appear as a standalone match, only "losses" does
    assert result.negative_count == 1
    assert words(result.negative_words) == ["losses"]
    assert result.intensified_words == ["losses mounted sharply"]


def test_intensifier_amplifies_adjacent_word_weight():
    analyzer = SentimentAnalyzer(TEST_LEXICON)
    plain = analyzer.analyze("The outlook was good.")
    intensified = analyzer.analyze("The outlook was surprisingly good.")
    amplified = analyzer.analyze("Losses mounted sharply this year.")
    plain_losses = analyzer.analyze("Losses mounted this year.")

    # a non-intensifier word before "good" doesn't change anything
    assert intensified.weighted_score == plain.weighted_score
    # but "sharply" next to "losses" should make its weight more negative
    assert amplified.weighted_score < plain_losses.weighted_score
    # counts (net_score) are unaffected - only the weighted_score changes
    assert amplified.net_score == plain_losses.net_score


def test_diminisher_does_not_count_as_its_own_word():
    analyzer = SentimentAnalyzer(TEST_LEXICON)
    result = analyzer.analyze("Losses mounted slightly this year.")

    assert result.negative_count == 1
    assert words(result.negative_words) == ["losses"]
    assert result.diminished_words == ["losses mounted slightly"]


def test_diminisher_shrinks_adjacent_word_weight():
    analyzer = SentimentAnalyzer(TEST_LEXICON)
    diminished = analyzer.analyze("Losses mounted slightly this year.")
    plain_losses = analyzer.analyze("Losses mounted this year.")

    assert abs(diminished.weighted_score) < abs(plain_losses.weighted_score)
    assert diminished.net_score == plain_losses.net_score


def test_directional_word_reported_with_topic_source_and_audit_phrase():
    analyzer = SentimentAnalyzer(TEST_LEXICON)
    result = analyzer.analyze("Profits fell sharply this quarter.")

    assert result.negative_count == 1
    match = result.negative_words[0]
    assert match.word == "fell"
    assert match.source == "TOPIC"
    assert result.directional_words == ["profits fell"]


def test_directional_word_with_no_topic_contributes_nothing():
    analyzer = SentimentAnalyzer(TEST_LEXICON)
    result = analyzer.analyze("The stock fell this quarter.")

    assert result.positive_count == 0
    assert result.negative_count == 0
    assert result.directional_words == []


def test_profits_fell_is_negative_end_to_end():
    analyzer = SentimentAnalyzer(load_combined_lexicon())
    result = analyzer.analyze("Profits fell sharply in the latest quarter.")

    assert result.net_score < 0


def test_costs_fell_is_positive_end_to_end():
    analyzer = SentimentAnalyzer(load_combined_lexicon())
    result = analyzer.analyze("Costs fell sharply in the latest quarter.")

    assert result.net_score > 0


def test_decline_and_gain_are_migrated_off_flat_lm_scoring():
    """
    "decline"/"gain" used to be flat LM entries (-1.0/+1.0). They're now
    intercepted by the directional-topic system before the lexicon lookup
    ever runs, so with no topic noun nearby they contribute nothing at all -
    a flat LM match would have scored them regardless of context.
    """
    analyzer = SentimentAnalyzer(load_combined_lexicon())
    result = analyzer.analyze("The company saw a decline. There was also a gain.")

    assert result.positive_count == 0
    assert result.negative_count == 0
    assert result.net_score == 0
