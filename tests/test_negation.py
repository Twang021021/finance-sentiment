from finance_sentiment.negation import find_negation_cue_index


def test_finds_cue_immediately_before():
    tokens = ["the", "results", "were", "not", "good"]
    assert find_negation_cue_index(tokens, 4) == 3


def test_finds_cue_within_window():
    tokens = ["not", "particularly", "very", "good"]
    assert find_negation_cue_index(tokens, 3) == 0


def test_returns_none_outside_window():
    tokens = ["not", "a", "b", "c", "good"]
    # "not" is 4 tokens before "good", beyond the default window of 3
    assert find_negation_cue_index(tokens, 4) is None


def test_returns_none_when_no_cue_present():
    tokens = ["the", "results", "were", "very", "good"]
    assert find_negation_cue_index(tokens, 4) is None


def test_returns_closest_cue_when_multiple_present():
    tokens = ["never", "not", "good"]
    assert find_negation_cue_index(tokens, 2) == 1


def test_custom_window_size():
    tokens = ["not", "a", "b", "c", "d", "good"]
    assert find_negation_cue_index(tokens, 5, window=3) is None
    assert find_negation_cue_index(tokens, 5, window=5) == 0