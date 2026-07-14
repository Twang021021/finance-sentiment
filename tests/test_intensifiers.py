from finance_sentiment.intensifiers import find_effect, is_intensifier


def test_is_intensifier():
    assert is_intensifier("sharply")
    assert is_intensifier("greatly")
    assert not is_intensifier("good")
    assert not is_intensifier("excessively")  # deliberately left out, see intensifiers.py


def test_find_effect_when_intensifier_precedes_word():
    tokens = ["sales", "declined", "sharply", "this", "year"]
    effect = find_effect(tokens, 1)

    assert effect is not None
    assert effect.multiplier > 1.0
    assert effect.phrase == "declined sharply"


def test_find_effect_when_intensifier_follows_word():
    tokens = ["greatly", "improved", "results"]
    effect = find_effect(tokens, 1)

    assert effect is not None
    assert effect.multiplier > 1.0
    assert effect.phrase == "greatly improved"


def test_find_effect_returns_none_when_no_intensifier_nearby():
    tokens = ["the", "results", "were", "good"]
    assert find_effect(tokens, 3) is None


def test_find_effect_ignores_intensifiers_outside_window():
    tokens = ["sharply", "a", "b", "c", "good"]
    # "sharply" is 4 tokens away from "good", outside the default window of 3
    assert find_effect(tokens, 4) is None


def test_find_effect_uses_only_the_closest_intensifier():
    tokens = ["greatly", "sharply", "improved"]
    effect = find_effect(tokens, 2)

    # "sharply" (distance 1) is closer than "greatly" (distance 2) to "improved" -
    # only the closest one's multiplier applies, they don't stack
    assert effect is not None
    assert effect.phrase == "sharply improved"
