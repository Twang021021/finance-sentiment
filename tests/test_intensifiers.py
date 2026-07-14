from finance_sentiment.intensifiers import adjacent_multiplier, is_intensifier


def test_is_intensifier():
    assert is_intensifier("sharply")
    assert is_intensifier("greatly")
    assert not is_intensifier("good")
    assert not is_intensifier("excessively")  # deliberately left out, see intensifiers.py


def test_multiplier_when_intensifier_precedes_word():
    tokens = ["sales", "declined", "sharply", "this", "year"]
    assert adjacent_multiplier(tokens, 1) > 1.0


def test_multiplier_when_intensifier_follows_word():
    tokens = ["greatly", "improved", "results"]
    assert adjacent_multiplier(tokens, 1) > 1.0


def test_multiplier_is_one_when_no_intensifier_nearby():
    tokens = ["the", "results", "were", "good"]
    assert adjacent_multiplier(tokens, 3) == 1.0


def test_multiplier_ignores_intensifiers_outside_window():
    tokens = ["sharply", "a", "b", "c", "good"]
    # "sharply" is 4 tokens away from "good", outside the default window of 2
    assert adjacent_multiplier(tokens, 4) == 1.0


def test_multiple_adjacent_intensifiers_stack():
    tokens = ["greatly", "sharply", "improved"]
    single = adjacent_multiplier(["greatly", "improved"], 1)
    stacked = adjacent_multiplier(tokens, 2)
    assert stacked > single