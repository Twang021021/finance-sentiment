from finance_sentiment.diminishers import find_effect, is_diminisher


def test_is_diminisher():
    assert is_diminisher("slightly")
    assert is_diminisher("barely")
    assert not is_diminisher("good")
    assert not is_diminisher("sharply")  # that's an intensifier, not a diminisher


def test_find_effect_when_diminisher_precedes_word():
    tokens = ["sales", "declined", "slightly", "this", "year"]
    effect = find_effect(tokens, 1)

    assert effect is not None
    assert effect.multiplier < 1.0
    assert effect.phrase == "declined slightly"


def test_find_effect_when_diminisher_follows_word():
    tokens = ["somewhat", "improved", "results"]
    effect = find_effect(tokens, 1)

    assert effect is not None
    assert effect.multiplier < 1.0
    assert effect.phrase == "somewhat improved"


def test_find_effect_returns_none_when_no_diminisher_nearby():
    tokens = ["the", "results", "were", "good"]
    assert find_effect(tokens, 3) is None


def test_find_effect_ignores_diminishers_outside_window():
    tokens = ["barely", "a", "b", "c", "good"]
    assert find_effect(tokens, 4) is None


def test_find_effect_uses_only_the_closest_diminisher():
    tokens = ["somewhat", "slightly", "improved"]
    effect = find_effect(tokens, 2)

    assert effect is not None
    assert effect.phrase == "slightly improved"
