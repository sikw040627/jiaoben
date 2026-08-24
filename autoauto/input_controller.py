"""High-level input: taps, long-press, swipes with optional humanised timing.

Built purely on the ADB `input` verbs (no root required). For a truly
continuous multi-point gesture (finger never lifts) use the UiAutomator2
controller in `ui.py`, which exposes `gesture()` via `swipe_points`.

`randomize` adds small, honest variation — a few pixels of landing jitter and a
little duration wobble — so repeated actions are not pixel-and-millisecond
identical. It does not conceal anything; it just makes flicks land reliably and
motion look less robotic.
"""
from __future__ import annotations

import random

from .device import DeviceProtocol
from .geometry import Point, ResolutionAdapter
from .logging_conf import get_logger

log = get_logger("input")


class InputController:
    def __init__(self, device: DeviceProtocol,
                 adapter: ResolutionAdapter | None = None,
                 rng: random.Random | None = None,
                 randomize: bool = True) -> None:
        self.device = device
        self.adapter = adapter
        self.rng = rng or random.Random()
        self.randomize = randomize

    # -- helpers --------------------------------------------------------
    def _resolve(self, x: int, y: int, jitter: int = 0) -> Point:
        p = Point(int(x), int(y))
        if self.adapter is not None:
            p = self.adapter.scale_point(p)
        if self.randomize and jitter > 0:
            p = p.jitter(jitter, self.rng)
        return p

    def _wobble_ms(self, base: int, frac: float = 0.15) -> int:
        if not self.randomize:
            return base
        return max(1, int(base * (1 + self.rng.uniform(-frac, frac))))

    # -- gestures -------------------------------------------------------
    def tap(self, x: int, y: int, jitter: int = 2) -> Point:
        p = self._resolve(x, y, jitter)
        self.device.tap(p.x, p.y)
        log.debug("tap %s", p.as_tuple())
        return p

    def long_press(self, x: int, y: int, duration_ms: int = 600,
                   jitter: int = 2) -> Point:
        p = self._resolve(x, y, jitter)
        dur = self._wobble_ms(duration_ms)
        # A zero-length swipe with a duration is the standard long-press trick.
        self.device.swipe(p.x, p.y, p.x, p.y, dur)
        log.debug("long_press %s %dms", p.as_tuple(), dur)
        return p

    def swipe(self, x1: int, y1: int, x2: int, y2: int,
              duration_ms: int = 300, jitter: int = 2) -> tuple[Point, Point]:
        a = self._resolve(x1, y1, jitter)
        b = self._resolve(x2, y2, jitter)
        dur = self._wobble_ms(duration_ms)
        self.device.swipe(a.x, a.y, b.x, b.y, dur)
        log.debug("swipe %s -> %s %dms", a.as_tuple(), b.as_tuple(), dur)
        return a, b

    # convenient directional swipes for scrolling lists ----------------
    def scroll(self, direction: str, distance: int = 600,
               center: Point | None = None, duration_ms: int = 400) -> None:
        w, h = self.device.window_size()
        c = center or Point(w // 2, h // 2)
        dx, dy = {"up": (0, -1), "down": (0, 1),
                  "left": (-1, 0), "right": (1, 0)}[direction]
        self.swipe(c.x, c.y, c.x + dx * distance, c.y + dy * distance,
                   duration_ms=duration_ms, jitter=0)

    # -- keys / text ----------------------------------------------------
    def key(self, keycode: int | str) -> None:
        self.device.keyevent(keycode)

    def back(self) -> None:
        self.device.keyevent("KEYCODE_BACK")

    def home(self) -> None:
        self.device.keyevent("KEYCODE_HOME")

    def text(self, s: str) -> None:
        self.device.input_text(s)
