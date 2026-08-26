"""Record & replay of input actions.

`Recorder` builds a timed list of `Action`s (either programmatically or fed from
a live getevent stream — see getevent.py). `Player` replays that list against an
InputController, preserving the original inter-action timing.

Both the clock and the sleep function are injectable so replay can be unit
tested deterministically with no real device and no real waiting.
"""
from __future__ import annotations

import time
from typing import Callable

from .actions import Action, load_actions, rebase_to_zero, save_actions
from .input_controller import InputController
from .logging_conf import get_logger

log = get_logger("recorder")


class Recorder:
    """Accumulates actions with millisecond timestamps from a start marker."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._start: float | None = None
        self.actions: list[Action] = []

    def start(self) -> "Recorder":
        self._start = self._clock()
        self.actions.clear()
        return self

    def _now_ms(self) -> int:
        if self._start is None:
            self.start()
        return int((self._clock() - self._start) * 1000)

    def add(self, kind: str, **params) -> Action:
        a = Action(kind=kind, at_ms=self._now_ms(), params=params)
        self.actions.append(a)
        return a

    # convenience wrappers ---------------------------------------------
    def tap(self, x: int, y: int) -> Action:
        return self.add("tap", x=x, y=y)

    def long_press(self, x: int, y: int, duration_ms: int = 600) -> Action:
        return self.add("long_press", x=x, y=y, duration_ms=duration_ms)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> Action:
        return self.add("swipe", x1=x1, y1=y1, x2=x2, y2=y2, duration_ms=duration_ms)

    def key(self, keycode: int | str) -> Action:
        return self.add("key", keycode=keycode)

    def text(self, s: str) -> Action:
        return self.add("text", s=s)

    def wait(self, ms: int) -> Action:
        """Record an explicit pause (replayed as a sleep)."""
        return self.add("wait", ms=int(ms))

    def trim_lead(self) -> "Recorder":
        """Drop dead lead-in time so the first action starts at 0ms."""
        self.actions = rebase_to_zero(self.actions)
        return self

    def save(self, path) -> None:
        save_actions(self.actions, path)

    def to_sh(self, **kwargs) -> str:
        """Compile the recording to an on-device shell script (text)."""
        from .shscript import actions_to_sh
        return actions_to_sh(self.actions, **kwargs)

    def save_sh(self, path, **kwargs) -> None:
        """Compile the recording and write it as a `.sh` file."""
        from .shscript import save_sh
        save_sh(self.actions, path, **kwargs)


class Player:
    """Replays a list of actions, honouring their relative timing."""

    def __init__(self, controller: InputController,
                 sleep: Callable[[float], None] = time.sleep,
                 speed: float = 1.0) -> None:
        self.controller = controller
        self._sleep = sleep
        self.speed = speed if speed > 0 else 1.0

    def play(self, actions: list[Action], loops: int = 1) -> int:
        """Replay `actions` `loops` times. Returns total actions dispatched."""
        dispatched = 0
        for _ in range(loops):
            prev_ms = 0
            for a in actions:
                gap = (a.at_ms - prev_ms) / 1000.0 / self.speed
                if gap > 0:
                    self._sleep(gap)
                self._dispatch(a)
                prev_ms = a.at_ms
                dispatched += 1
        return dispatched

    def play_file(self, path, loops: int = 1) -> int:
        return self.play(load_actions(path), loops=loops)

    def _dispatch(self, a: Action) -> None:
        p = a.params
        if a.kind == "tap":
            self.controller.tap(p["x"], p["y"])
        elif a.kind == "long_press":
            self.controller.long_press(p["x"], p["y"], p.get("duration_ms", 600))
        elif a.kind == "swipe":
            self.controller.swipe(p["x1"], p["y1"], p["x2"], p["y2"],
                                  p.get("duration_ms", 300))
        elif a.kind == "key":
            self.controller.key(p["keycode"])
        elif a.kind == "text":
            self.controller.text(p["s"])
        elif a.kind == "wait":
            self._sleep(p.get("ms", 0) / 1000.0)
        else:  # pragma: no cover - guarded by Action validation
            raise ValueError(f"cannot dispatch action kind {a.kind!r}")
