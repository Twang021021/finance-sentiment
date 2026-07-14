from finance_sentiment.analyzer import SentimentAnalyzer
from finance_sentiment.lexicon import LexiconEntry

TEST_LEXICON = {
    "profitable": LexiconEntry(1.0, "LM"),
    "strong": LexiconEntry(1.0, "LM"),
    "bankruptcy": LexiconEntry(-1.0, "LM"),
    "losses": LexiconEntry(-1.0, "LM"),
    "decline": LexiconEntry(-1.0, "LM"),
    "surge": LexiconEntry(1.0, "HIV4"),
    "good": LexiconEntry(1.0, "LM"),
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
    assert sources["surged"] == "HIV4"
    assert sources["profitable"] == "LM"


def test_lemmatization_matches_inflected_forms_but_reports_surface_word():
    analyzer = SentimentAnalyzer(TEST_LEXICON)
    # "declining" isn't in TEST_LEXICON directly, only its lemma "decline" is.
    result = analyzer.analyze("Revenue was declining this quarter.")

    assert result.negative_count == 1
    # the reported word is the surface form actually seen in the text...
    assert words(result.negative_words) == ["declining"]
    # ...not the lemma used to find the match.
    assert "decline" not in words(result.negative_words)


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
    result = analyzer.analyze("Sales declined sharply this year.")

    # "sharply" must not appear as a standalone match, only "declined" does
    assert result.negative_count == 1
    assert words(result.negative_words) == ["declined"]


def test_intensifier_amplifies_adjacent_word_weight():
    analyzer = SentimentAnalyzer(TEST_LEXICON)
    plain = analyzer.analyze("The outlook was good.")
    intensified = analyzer.analyze("The outlook was surprisingly good.")
    amplified = analyzer.analyze("Sales declined sharply this year.")
    plain_decline = analyzer.analyze("Sales declined this year.")

    # a non-intensifier word before "good" doesn't change anything
    assert intensified.weighted_score == plain.weighted_score
    # but "sharply" next to "declined" should make its weight more negative
    assert amplified.weighted_score < plain_decline.weighted_score
    # counts (net_score) are unaffected - only the weighted_score changes
    assert amplified.net_score == plain_decline.net_score