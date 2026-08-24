"""Pluggable OCR (文字识别).

Core features work without OCR, so no heavy OCR dependency is forced. Two
optional backends are supported and auto-detected:

  * pytesseract  (needs the Tesseract binary on PATH)  -- light
  * easyocr      (pulls in torch)                       -- heavier, better CJK

Usage:
    engine = get_ocr_engine()          # auto-pick whatever is installed
    text = engine.read_text(img, region)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from .errors import OCRUnavailableError
from .geometry import Rect


@dataclass
class OCRWord:
    text: str
    rect: Rect
    confidence: float


def _crop(image: np.ndarray, region: Rect | None) -> np.ndarray:
    if region is None:
        return image
    rows, cols = region.as_slice()
    return image[rows, cols]


class OCREngine(Protocol):
    def recognize(self, image: np.ndarray, region: Rect | None = ...) -> list[OCRWord]: ...
    def read_text(self, image: np.ndarray, region: Rect | None = ...) -> str: ...


class TesseractEngine:
    def __init__(self, lang: str = "eng") -> None:
        import pytesseract  # noqa: F401  (import-time availability check)
        self._pt = pytesseract
        self.lang = lang

    def recognize(self, image: np.ndarray, region: Rect | None = None) -> list[OCRWord]:
        img = _crop(image, region)
        data = self._pt.image_to_data(img, lang=self.lang,
                                      output_type=self._pt.Output.DICT)
        ox, oy = (region.left, region.top) if region else (0, 0)
        words: list[OCRWord] = []
        for i, txt in enumerate(data["text"]):
            if not txt.strip():
                continue
            l, t = data["left"][i] + ox, data["top"][i] + oy
            w, h = data["width"][i], data["height"][i]
            conf = float(data["conf"][i]) if data["conf"][i] != "-1" else 0.0
            words.append(OCRWord(txt, Rect(l, t, l + w, t + h), conf))
        return words

    def read_text(self, image: np.ndarray, region: Rect | None = None) -> str:
        return self._pt.image_to_string(_crop(image, region), lang=self.lang).strip()


class EasyOCREngine:
    def __init__(self, langs: list[str] | None = None) -> None:
        import easyocr
        self._reader = easyocr.Reader(langs or ["en"])

    def recognize(self, image: np.ndarray, region: Rect | None = None) -> list[OCRWord]:
        img = _crop(image, region)
        ox, oy = (region.left, region.top) if region else (0, 0)
        words: list[OCRWord] = []
        for box, text, conf in self._reader.readtext(img):
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            l, t, r, b = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
            words.append(OCRWord(text, Rect(l + ox, t + oy, r + ox, b + oy), float(conf)))
        return words

    def read_text(self, image: np.ndarray, region: Rect | None = None) -> str:
        return " ".join(w.text for w in self.recognize(image, region))


def get_ocr_engine(prefer: str | None = None, **kwargs) -> OCREngine:
    """Return an available OCR engine.

    :param prefer: "tesseract" or "easyocr" to force a backend.
    :raises OCRUnavailableError: when the requested/any backend is missing.
    """
    order = [prefer] if prefer else ["tesseract", "easyocr"]
    errors = []
    for name in order:
        try:
            if name == "tesseract":
                return TesseractEngine(**kwargs)
            if name == "easyocr":
                return EasyOCREngine(**kwargs)
        except Exception as e:  # backend not installed / not configured
            errors.append(f"{name}: {e}")
    raise OCRUnavailableError(
        "no OCR backend available. Install one:\n"
        "  pip install pytesseract   (+ Tesseract binary on PATH)\n"
        "  pip install easyocr\n"
        f"tried: {errors}")
