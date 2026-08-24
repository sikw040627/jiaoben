"""Human-like motion helpers.

自动精灵 replays are often dead-straight, constant-speed drags between exact
pixels. Real fingers move along a curve, accelerate then decelerate, and never
land on the exact same pixel twice. These helpers generate such paths so a
legitimate automation still behaves smoothly (and, incidentally, feels natural).

Nothing here hides the tool or evades anything — it just produces nicer motion
than a straight teleport, which also makes swipes register more reliably on
flick-sensitive UIs.
"""
from __future__ import annotations

import math
import random

from .geometry import Point


def _ease_in_out(t: float) -> float:
    """Smoothstep easing: slow start, fast middle, slow end. t in [0,1]."""
    return t * t * (3 - 2 * t)


def bezier_path(start: Point, end: Point, steps: int = 24,
                curviness: float = 0.25,
                rng: random.Random | None = None) -> list[Point]:
    """Quadratic Bezier path from start to end with a random control point.

    :param steps: number of intermediate samples (>= 2).
    :param curviness: how far the control point bows off the straight line,
        as a fraction of the segment length.
    :returns: list of Points including both endpoints, eased in time.
    """
    r = rng or random
    steps = max(2, steps)

    dx = end.x - start.x
    dy = end.y - start.y
    length = math.hypot(dx, dy) or 1.0

    # Perpendicular unit vector, control point bowed to one random side.
    px, py = -dy / length, dx / length
    bow = r.uniform(-curviness, curviness) * length
    mx = (start.x + end.x) / 2 + px * bow
    my = (start.y + end.y) / 2 + py * bow

    pts: list[Point] = []
    for i in range(steps):
        t = _ease_in_out(i / (steps - 1))
        # Quadratic Bezier: (1-t)^2 P0 + 2(1-t)t C + t^2 P1
        u = 1 - t
        x = u * u * start.x + 2 * u * t * mx + t * t * end.x
        y = u * u * start.y + 2 * u * t * my + t * t * end.y
        pts.append(Point(round(x), round(y)))
    return pts


def path_durations(steps: int, total_ms: int,
                   rng: random.Random | None = None,
                   jitter: float = 0.15) -> list[int]:
    """Split a total duration into per-segment ms with mild random jitter.

    :param steps: number of points; returns (steps-1) segment durations.
    :param total_ms: total gesture duration.
    :param jitter: fractional random variation per segment.
    """
    r = rng or random
    n = max(1, steps - 1)
    base = total_ms / n
    raw = [max(1.0, base * (1 + r.uniform(-jitter, jitter))) for _ in range(n)]
    scale = total_ms / sum(raw)
    out = [max(1, round(v * scale)) for v in raw]
    # Correct rounding drift so the segments sum to exactly total_ms.
    drift = total_ms - sum(out)
    out[-1] = max(1, out[-1] + drift)
    return out
