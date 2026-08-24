import random

from autoauto.geometry import Point
from autoauto.humanize import bezier_path, path_durations


def test_bezier_endpoints_and_count():
    a, b = Point(0, 0), Point(100, 50)
    path = bezier_path(a, b, steps=20, rng=random.Random(0))
    assert len(path) == 20
    assert path[0] == a
    assert path[-1] == b


def test_bezier_min_steps():
    path = bezier_path(Point(0, 0), Point(10, 10), steps=1)
    assert len(path) == 2  # clamped to >= 2


def test_path_durations_sum_matches_total():
    d = path_durations(steps=10, total_ms=500, rng=random.Random(3))
    assert len(d) == 9
    assert sum(d) == 500  # rescaled to exactly the requested total
    assert all(v >= 1 for v in d)


def test_path_durations_single_segment():
    d = path_durations(steps=2, total_ms=120, rng=random.Random(3))
    assert d == [120]
