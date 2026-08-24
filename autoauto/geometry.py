"""Geometry helpers: points, rectangles and resolution adaptation.

自动精灵-style scripts are usually written against one reference resolution and
then run on devices with a different screen size. `ResolutionAdapter` scales
coordinates so a script recorded on e.g. 1080x1920 keeps working on 720x1280.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    x: int
    y: int

    def as_tuple(self) -> tuple[int, int]:
        return (self.x, self.y)

    def offset(self, dx: int, dy: int) -> "Point":
        return Point(self.x + dx, self.y + dy)

    def jitter(self, radius: int, rng: random.Random | None = None) -> "Point":
        """Return a nearby point within a square of +/-radius (uniform)."""
        if radius <= 0:
            return self
        r = rng or random
        return Point(self.x + r.randint(-radius, radius),
                     self.y + r.randint(-radius, radius))


@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def center(self) -> Point:
        return Point((self.left + self.right) // 2, (self.top + self.bottom) // 2)

    def contains(self, p: Point) -> bool:
        return self.left <= p.x < self.right and self.top <= p.y < self.bottom

    def as_slice(self) -> tuple[slice, slice]:
        """(rows, cols) slice for indexing a numpy image[top:bottom, left:right]."""
        return (slice(self.top, self.bottom), slice(self.left, self.right))


class ResolutionAdapter:
    """Scale coordinates from a reference resolution to the live device size."""

    def __init__(self, ref_width: int, ref_height: int,
                 dev_width: int, dev_height: int) -> None:
        if ref_width <= 0 or ref_height <= 0:
            raise ValueError("reference resolution must be positive")
        self.ref_width = ref_width
        self.ref_height = ref_height
        self.dev_width = dev_width
        self.dev_height = dev_height
        self.sx = dev_width / ref_width
        self.sy = dev_height / ref_height

    def scale_point(self, p: Point) -> Point:
        return Point(round(p.x * self.sx), round(p.y * self.sy))

    def scale_rect(self, r: Rect) -> Rect:
        return Rect(round(r.left * self.sx), round(r.top * self.sy),
                    round(r.right * self.sx), round(r.bottom * self.sy))
