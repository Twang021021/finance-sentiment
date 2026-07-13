from finance_sentiment.analyzer import SentimentAnalyzer

TEST_LEXICON = {
    "profitable": 1.0,
    "strong": 1.0,
    "bankruptcy": -1.0,
    "losses": -1.0,
}


def test_analyze_counts_and_words():
    analyzer = SentimentAnalyzer(TEST_LEXICON)
    result = analyzer.analyze("The company is profitable and strong despite some losses.")

    assert result.positive_count == 2
    assert result.negative_count == 1
    assert result.positive_words == ["profitable", "strong"]
    assert result.negative_words == ["losses"]
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
