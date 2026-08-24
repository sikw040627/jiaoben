"""Stability helpers: frame-difference (stuck detection), wait-until-stable, and
app restart.

Loading screens, animations and "stuck" states are handled by comparing
successive frames. App restart uses plain `am` shell verbs. Frame math is pure
and unit-tested; app control just issues shell commands.
"""
from __future__ import annotations

import time
from typing import Callable

import numpy as np

from .device import DeviceProtocol
from .geometry import Rect
from .logging_conf import get_logger

log = get_logger("stability")


def _crop(img: np.ndarray, region: Rect | None) -> np.ndarray:
    if region is None:
        return img
    rows, cols = region.as_slice()
    return img[rows, cols]


def frame_diff_ratio(a: np.ndarray, b: np.ndarray, tolerance: int = 10,
                     region: Rect | None = None) -> float:
    """Fraction (0..1) of pixels differing by more than `tolerance` in any channel."""
    ca, cb = _crop(a, region), _crop(b, region)
    if ca.shape != cb.shape:
        return 1.0
    diff = np.abs(ca.astype(np.int16) - cb.astype(np.int16))
    changed = np.any(diff > tolerance, axis=2)
    total = changed.size
    return float(changed.sum()) / total if total else 0.0


def frames_similar(a: np.ndarray, b: np.ndarray, tolerance: int = 10,
                   max_diff_ratio: float = 0.02, region: Rect | None = None) -> bool:
    return frame_diff_ratio(a, b, tolerance, region) <= max_diff_ratio


def wait_until_stable(engine, region: Rect | None = None, tolerance: int = 10,
                      max_diff_ratio: float = 0.01, timeout: float = 10.0,
                      interval: float = 0.4, stable_frames: int = 2) -> bool:
    """Poll the screen until it stops changing for `stable_frames` consecutive
    comparisons (e.g. a loading spinner finished). Returns True if it settled.
    """
    deadline = engine._clock() + timeout
    prev = engine.frame(force=True)
    consecutive = 0
    while engine._clock() < deadline:
        engine.sleep(interval)
        cur = engine.frame(force=True)
        if frames_similar(prev, cur, tolerance, max_diff_ratio, region):
            consecutive += 1
            if consecutive >= stable_frames:
                return True
        else:
            consecutive = 0
        prev = cur
    return False


# -- app lifecycle ----------------------------------------------------------
def force_stop(device: DeviceProtocol, package: str) -> None:
    device.shell(f"am force-stop {package}")


def start_app(device: DeviceProtocol, package: str,
              activity: str | None = None) -> None:
    if activity:
        device.shell(f"am start -n {package}/{activity}")
    else:
        # Launch the default launchable activity for the package.
        device.shell(f"monkey -p {package} -c android.intent.category.LAUNCHER 1")


def restart_app(device: DeviceProtocol, package: str, activity: str | None = None,
                wait: float = 2.0, sleep: Callable[[float], None] = time.sleep) -> None:
    """Force-stop then relaunch an app (recovery from a wedged state)."""
    force_stop(device, package)
    sleep(wait)
    start_app(device, package, activity)
    log.info("restarted app %s", package)
