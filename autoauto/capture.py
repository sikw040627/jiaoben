"""Screen capture decoding.

Turns raw PNG bytes from the device into a BGR numpy image (OpenCV convention)
and offers a tiny cache so repeated vision queries in one "frame" don't trigger
multiple screencaps.
"""
from __future__ import annotations

import time

import cv2
import numpy as np

from .device import DeviceProtocol
from .geometry import Rect


def decode_png(png_bytes: bytes) -> np.ndarray:
    """Decode PNG bytes to a BGR uint8 image."""
    arr = np.frombuffer(png_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("failed to decode screenshot bytes")
    return img


def crop(img: np.ndarray, region: Rect | None) -> np.ndarray:
    if region is None:
        return img
    rows, cols = region.as_slice()
    return img[rows, cols]


class ScreenCache:
    """Grabs and caches a frame for a short TTL to avoid redundant screencaps."""

    def __init__(self, device: DeviceProtocol, ttl: float = 0.0,
                 clock=time.monotonic) -> None:
        self.device = device
        self.ttl = ttl
        self._clock = clock
        self._frame: np.ndarray | None = None
        self._stamp = 0.0

    def grab(self, force: bool = False) -> np.ndarray:
        now = self._clock()
        if (not force and self._frame is not None
                and (now - self._stamp) <= self.ttl):
            return self._frame
        self._frame = decode_png(self.device.screencap_png())
        self._stamp = now
        return self._frame

    def invalidate(self) -> None:
        self._frame = None
