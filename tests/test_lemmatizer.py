from finance_sentiment.lemmatizer import lemmatize


def test_lemmatize_regular_inflection():
    assert lemmatize("declining") == "decline"
    assert lemmatize("declined") == "decline"


def test_lemmatize_irregular_verb():
    assert lemmatize("sank") == "sink"


def test_lemmatize_already_base_form_is_unchanged():
    assert lemmatize("strong") == "strong"