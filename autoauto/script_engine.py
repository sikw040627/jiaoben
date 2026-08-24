"""Script orchestration layer.

Ties together capture + vision + input + ocr into the verbs a script author
actually uses, plus the control-flow helpers 自动精灵 provides: variables,
wait-for-image, find-and-tap, wait-until-condition, bounded retries and loops.

Scripts are ordinary Python using an `Engine` instance, e.g.:

    eng = Engine(device)
    if eng.find_and_tap("assets/start.png", timeout=10):
        eng.wait_image("assets/home.png", timeout=15)

Time is injectable (clock + sleep) so scripts and helpers unit-test without real
waiting or a real device.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from . import vision
from .capture import ScreenCache
from .device import DeviceProtocol
from .errors import TargetNotFoundError
from .geometry import Point, Rect, ResolutionAdapter
from .input_controller import InputController
from .logging_conf import get_logger
from .vision import MatchResult

log = get_logger("engine")

Template = "str | Path | np.ndarray"


class Context:
    """Simple variable store shared across a script run."""

    def __init__(self, **initial) -> None:
        self._vars: dict[str, object] = dict(initial)

    def set(self, name: str, value) -> None:
        self._vars[name] = value

    def get(self, name: str, default=None):
        return self._vars.get(name, default)

    def incr(self, name: str, by: int = 1) -> int:
        val = int(self._vars.get(name, 0)) + by
        self._vars[name] = val
        return val

    def __contains__(self, name: str) -> bool:
        return name in self._vars

    def as_dict(self) -> dict:
        return dict(self._vars)


_TEMPLATE_CACHE: dict[str, np.ndarray] = {}


def load_template(tpl) -> np.ndarray:
    """Load a template from a path (cached) or pass through a numpy array."""
    if isinstance(tpl, np.ndarray):
        return tpl
    key = str(tpl)
    if key not in _TEMPLATE_CACHE:
        img = cv2.imread(key, cv2.IMREAD_COLOR)
        if img is None:
            raise FileNotFoundError(f"template not found or unreadable: {key}")
        _TEMPLATE_CACHE[key] = img
    return _TEMPLATE_CACHE[key]


class Engine:
    def __init__(self, device: DeviceProtocol,
                 adapter: ResolutionAdapter | None = None,
                 randomize: bool = True,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep,
                 screen_ttl: float = 0.0) -> None:
        self.device = device
        self.ctx = Context()
        self.input = InputController(device, adapter=adapter, randomize=randomize)
        self._clock = clock
        self._sleep = sleep
        self.screen = ScreenCache(device, ttl=screen_ttl, clock=clock)
        self._ocr = None  # lazily created

    # -- capture --------------------------------------------------------
    def frame(self, force: bool = True) -> np.ndarray:
        return self.screen.grab(force=force)

    # -- vision verbs ---------------------------------------------------
    def find_image(self, tpl, threshold: float = 0.85,
                   region: Rect | None = None, multiscale: bool = False,
                   frame: np.ndarray | None = None) -> MatchResult:
        from .templateset import TemplateSet
        img = frame if frame is not None else self.frame()
        if isinstance(tpl, TemplateSet):
            return tpl.find(img, threshold, region)
        template = load_template(tpl)
        if multiscale:
            return vision.find_template_multiscale(img, template, threshold, region)
        return vision.find_template(img, template, threshold, region)

    def find_all_images(self, tpl, threshold: float = 0.85,
                        region: Rect | None = None) -> list[MatchResult]:
        return vision.find_all_templates(self.frame(), load_template(tpl),
                                         threshold, region)

    def find_color(self, rgb, tolerance: int = 12,
                   region: Rect | None = None) -> Point | None:
        return vision.find_color(self.frame(), rgb, tolerance, region)

    def pixel(self, x: int, y: int) -> tuple[int, int, int]:
        return vision.get_pixel(self.frame(), x, y)

    # -- waits ----------------------------------------------------------
    def wait_image(self, tpl, timeout: float = 10.0, interval: float = 0.5,
                   threshold: float = 0.85, region: Rect | None = None,
                   multiscale: bool = False, required: bool = False) -> MatchResult:
        """Poll until the image appears or timeout. Returns the MatchResult."""
        deadline = self._clock() + timeout
        last = MatchResult(False, 0.0)
        while True:
            last = self.find_image(tpl, threshold, region, multiscale)
            if last.found:
                return last
            if self._clock() >= deadline:
                if required:
                    raise TargetNotFoundError(
                        f"image not found within {timeout}s: {tpl}")
                return last
            self._sleep(interval)

    def wait_until(self, predicate: Callable[[], bool], timeout: float = 10.0,
                   interval: float = 0.3, required: bool = False) -> bool:
        deadline = self._clock() + timeout
        while True:
            if predicate():
                return True
            if self._clock() >= deadline:
                if required:
                    raise TargetNotFoundError("wait_until condition not met")
                return False
            self._sleep(interval)

    # -- combined actions ----------------------------------------------
    def find_and_tap(self, tpl, timeout: float = 0.0, threshold: float = 0.85,
                     region: Rect | None = None, multiscale: bool = False,
                     jitter: int = 3) -> bool:
        """Find an image (optionally waiting) and tap its centre."""
        if timeout > 0:
            res = self.wait_image(tpl, timeout, threshold=threshold,
                                  region=region, multiscale=multiscale)
        else:
            res = self.find_image(tpl, threshold, region, multiscale)
        if not res.found or res.center is None:
            return False
        self.input.tap(res.center.x, res.center.y, jitter=jitter)
        return True

    def tap_all(self, tpl, threshold: float = 0.85,
                region: Rect | None = None, jitter: int = 3) -> int:
        """Tap every occurrence of a template. Returns count tapped."""
        hits = self.find_all_images(tpl, threshold, region)
        for h in hits:
            if h.center:
                self.input.tap(h.center.x, h.center.y, jitter=jitter)
        return len(hits)

    # -- ocr ------------------------------------------------------------
    def ocr(self, region: Rect | None = None, prefer: str | None = None,
            preprocess: bool = False) -> str:
        """OCR a screen region to text.

        With `preprocess=True` the region is grayscaled/thresholded/upscaled
        first (helps small digit readouts like coins/HP/timers).
        """
        from .ocr import get_ocr_engine, preprocess_for_digits
        if self._ocr is None:
            self._ocr = get_ocr_engine(prefer=prefer)
        if preprocess:
            from .capture import crop
            img = preprocess_for_digits(crop(self.frame(), region))
            return self._ocr.read_text(img, None)
        return self._ocr.read_text(self.frame(), region)

    def read_number(self, region: Rect | None = None, prefer: str | None = None,
                    as_float: bool = False):
        """OCR a region and parse the number in it (coins / HP / countdown)."""
        from .numbers import parse_float, parse_int
        text = self.ocr(region=region, prefer=prefer, preprocess=True)
        return (parse_float(text, fix_confusions=True) if as_float
                else parse_int(text, fix_confusions=True))

    # -- misc -----------------------------------------------------------
    def sleep(self, seconds: float) -> None:
        self._sleep(seconds)

    def repeat(self, times: int, body: Callable[[int], None]) -> None:
        for i in range(times):
            body(i)
