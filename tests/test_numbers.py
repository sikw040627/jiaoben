from autoauto.numbers import parse_float, parse_int


def test_parse_int_basic():
    assert parse_int("Coins: 1,234") == 1234
    assert parse_int("-42 hp") == -42
    assert parse_int("no digits here") is None


def test_parse_int_ocr_confusions():
    # opt-in confusion fixing for known-numeric fields: O->0, l/I->1, S->5, B->8
    assert parse_int("lOl", fix_confusions=True) == 101
    assert parse_int("SB", fix_confusions=True) == 58
    # ...and OFF by default so words are not mangled into numbers
    assert parse_int("none") is None
    assert parse_int("lOl") is None


def test_parse_float():
    assert parse_float("3.14x") == 3.14
    assert parse_float("1,024.5") == 1024.5
    assert parse_float("trailing 7.") == 7.0
    assert parse_float("none") is None
