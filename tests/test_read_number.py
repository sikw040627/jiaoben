from autoauto import numbers
from autoauto.script_engine import Engine
from conftest import FakeDevice


class FakeOCR:
    """Stub OCR engine returning canned text regardless of the image."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0

    def read_text(self, image, region=None) -> str:
        self.calls += 1
        return self.text

    def recognize(self, image, region=None):
        return []


def make_engine(text: str):
    eng = Engine(FakeDevice())
    eng._ocr = FakeOCR(text)      # inject; skips real backend
    return eng


def test_read_int_parses_ocr_text():
    eng = make_engine("Coins: 1,234")
    assert numbers.read_int(eng) == 1234
    assert eng._ocr.calls == 1     # OCR actually invoked


def test_read_float_parses_ocr_text():
    eng = make_engine("3.14 fps")
    assert numbers.read_float(eng) == 3.14


def test_read_int_applies_confusions():
    eng = make_engine("lOO")       # OCR misread of 100
    assert numbers.read_int(eng) == 100


def test_read_int_none_when_no_number():
    eng = make_engine("---")       # no digits, no confusable letters
    assert numbers.read_int(eng) is None
