"""Shared test fixtures: a fake device and synthetic-image helpers.

Everything here lets the suite exercise the real framework logic with no adb,
no device, and no real sleeping.
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest


class FakeDevice:
    """In-memory DeviceProtocol implementation that records calls."""

    def __init__(self, width: int = 1080, height: int = 1920) -> None:
        self._w = width
        self._h = height
        self.frame = np.full((height, width, 3), 40, dtype=np.uint8)
        self.calls: list[tuple] = []

    # DeviceProtocol -----------------------------------------------------
    def shell(self, cmd: str, timeout=None) -> str:
        self.calls.append(("shell", cmd))
        return ""

    def screencap_png(self) -> bytes:
        ok, buf = cv2.imencode(".png", self.frame)
        assert ok
        return buf.tobytes()

    def window_size(self) -> tuple[int, int]:
        return (self._w, self._h)

    def tap(self, x: int, y: int) -> None:
        self.calls.append(("tap", x, y))

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int) -> None:
        self.calls.append(("swipe", x1, y1, x2, y2, duration_ms))

    def keyevent(self, keycode) -> None:
        self.calls.append(("key", keycode))

    def input_text(self, text: str) -> None:
        self.calls.append(("text", text))

    # test helpers -------------------------------------------------------
    def only(self, kind: str) -> list[tuple]:
        return [c for c in self.calls if c[0] == kind]


class FakeClock:
    """Deterministic monotonic clock; advance() moves virtual time forward.

    Used both as clock() and as sleep(dt) — sleeping simply advances time.
    """

    def __init__(self, start: float = 1000.0) -> None:
        self.t = start

    def __call__(self) -> float:  # clock()
        return self.t

    def sleep(self, dt: float) -> None:
        self.t += max(0.0, dt)

    def advance(self, dt: float) -> None:
        self.t += dt


def make_template(color=(0, 200, 0), size=(40, 40)) -> np.ndarray:
    """Create a *textured* BGR template patch.

    Solid-colour patches have zero variance and make TM_CCOEFF_NORMED degenerate
    (it matches everywhere). Real UI templates have texture, so the test
    templates add gradients, a border and a centre dot to be realistic and
    unambiguously locatable. `color` tints the green channel so different calls
    yield distinguishable templates.
    """
    h, w = size
    tpl = np.zeros((h, w, 3), dtype=np.uint8)
    tpl[:, :, 0] = np.linspace(0, 255, w, dtype=np.uint8)[None, :]  # B gradient
    tpl[:, :, 1] = color[1]                                          # G tint
    tpl[:, :, 2] = np.linspace(0, 255, h, dtype=np.uint8)[:, None]  # R gradient
    cv2.rectangle(tpl, (0, 0), (w - 1, h - 1), (255, 255, 255), 1)
    cv2.circle(tpl, (w // 2, h // 2), max(2, min(h, w) // 8), (0, 0, 0), -1)
    return tpl


def paste(scene: np.ndarray, patch: np.ndarray, x: int, y: int) -> np.ndarray:
    h, w = patch.shape[:2]
    scene[y:y + h, x:x + w] = patch
    return scene


@pytest.fixture
def device() -> FakeDevice:
    return FakeDevice()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()
