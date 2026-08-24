import random

from autoauto.geometry import Point, Rect, ResolutionAdapter


def test_point_offset_and_jitter_zero():
    p = Point(10, 20)
    assert p.offset(5, -5) == Point(15, 15)
    assert p.jitter(0) == p  # zero radius is a no-op


def test_point_jitter_bounded():
    rng = random.Random(1)
    p = Point(100, 100)
    for _ in range(200):
        j = p.jitter(5, rng)
        assert abs(j.x - 100) <= 5 and abs(j.y - 100) <= 5


def test_rect_center_contains_slice():
    r = Rect(10, 20, 30, 60)
    assert r.width == 20 and r.height == 40
    assert r.center == Point(20, 40)
    assert r.contains(Point(10, 20))
    assert not r.contains(Point(30, 60))  # right/bottom exclusive
    rows, cols = r.as_slice()
    assert rows == slice(20, 60) and cols == slice(10, 30)


def test_resolution_adapter_scaling():
    a = ResolutionAdapter(1080, 1920, 720, 1280)
    assert a.scale_point(Point(1080, 1920)) == Point(720, 1280)
    assert a.scale_point(Point(540, 960)) == Point(360, 640)
    r = a.scale_rect(Rect(0, 0, 1080, 960))
    assert r == Rect(0, 0, 720, 640)
