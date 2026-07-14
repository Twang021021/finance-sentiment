from finance_sentiment.directional import is_directional, resolve_weight


def test_is_directional():
    assert is_directional("fell")
    assert is_directional("rose")
    assert is_directional("declining")
    assert not is_directional("good")


def test_profits_fell_is_negative():
    tokens = ["profits", "fell"]
    result = resolve_weight(tokens, 1)

    assert result is not None
    weight, phrase = result
    assert weight < 0
    assert phrase == "profits fell"


def test_costs_fell_is_positive():
    tokens = ["costs", "fell"]
    result = resolve_weight(tokens, 1)

    assert result is not None
    weight, phrase = result
    assert weight > 0
    assert phrase == "costs fell"


def test_profits_rose_is_positive():
    tokens = ["profits", "rose"]
    result = resolve_weight(tokens, 1)

    assert result is not None
    weight, _phrase = result
    assert weight > 0


def test_costs_rose_is_negative():
    tokens = ["costs", "rose"]
    result = resolve_weight(tokens, 1)

    assert result is not None
    weight, _phrase = result
    assert weight < 0


def test_no_topic_nearby_returns_none():
    tokens = ["prices", "fell"]
    assert resolve_weight(tokens, 1) is None


def test_topic_outside_window_returns_none():
    tokens = ["profits", "a", "b", "c", "d", "fell"]
    assert resolve_weight(tokens, 5) is None


def test_erased_losses_is_positive():
    # "erased" is treated as a "down" direction (removing/eliminating);
    # erasing a negative-topic noun (losses) is good news.
    tokens = ["erased", "losses"]
    result = resolve_weight(tokens, 0)

    assert result is not None
    weight, phrase = result
    assert weight > 0
    assert phrase == "erased losses"


def test_erased_gains_is_negative():
    tokens = ["erased", "gains"]
    result = resolve_weight(tokens, 0)

    assert result is not None
    weight, _phrase = result
    assert weight < 0
