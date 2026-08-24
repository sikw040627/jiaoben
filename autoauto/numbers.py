"""Read numbers off the screen (coins / HP / countdowns).

`parse_int` / `parse_float` are pure text extractors (unit tested). `read_int`
runs OCR on a screen region then parses — it needs an OCR backend installed.
"""
from __future__ import annotations

import re

from .geometry import Rect

_INT_RE = re.compile(r"[-+]?\d[\d,]*")
_FLOAT_RE = re.compile(r"[-+]?\d[\d,]*\.?\d*")
# common OCR confusions for digits
_FIX = str.maketrans({"O": "0", "o": "0", "l": "1", "I": "1", "|": "1",
                      "S": "5", "B": "8"})


def parse_int(text: str, fix_confusions: bool = False) -> int | None:
    """Extract the first integer from `text` (commas allowed as separators).

    `fix_confusions` is OFF by default because letter->digit fixes create false
    positives on ordinary words ("none" -> 0). Turn it on only for fields known
    to be numeric (see `read_int`); it is applied as a fallback when the raw text
    has no digits at all.
    """
    m = _INT_RE.search(text)
    if not m and fix_confusions:
        m = _INT_RE.search(text.translate(_FIX))
    if not m:
        return None
    try:
        return int(m.group(0).replace(",", ""))
    except ValueError:
        return None


def parse_float(text: str, fix_confusions: bool = False) -> float | None:
    m = _FLOAT_RE.search(text)
    if not m and fix_confusions:
        m = _FLOAT_RE.search(text.translate(_FIX))
    if not m:
        return None
    token = m.group(0).replace(",", "").rstrip(".")
    try:
        return float(token)
    except ValueError:
        return None


def read_int(engine, region: Rect | None = None, prefer: str | None = None) -> int | None:
    """OCR a screen region (digit-preprocessed) and parse an integer.

    Needs an OCR backend installed (pytesseract or easyocr).
    """
    return engine.read_number(region=region, prefer=prefer, as_float=False)


def read_float(engine, region: Rect | None = None, prefer: str | None = None) -> float | None:
    """OCR a screen region (digit-preprocessed) and parse a float."""
    return engine.read_number(region=region, prefer=prefer, as_float=True)
