import numpy as np

from autoauto import vision
from autoauto.geometry import Rect
from conftest import make_template, paste


def blank(h=400, w=300, fill=30):
    return np.full((h, w, 3), fill, dtype=np.uint8)


def test_find_template_hit_and_center():
    scene = blank()
    tpl = make_template(color=(0, 200, 0), size=(40, 40))
    paste(scene, tpl, x=100, y=80)
    res = vision.find_template(scene, tpl, threshold=0.9)
    assert res.found
    assert res.center.as_tuple() == (100 + 20, 80 + 20)


def test_find_template_miss():
    scene = blank()
    tpl = make_template(color=(0, 0, 255), size=(30, 30))
    res = vision.find_template(scene, tpl, threshold=0.95)
    assert not res.found
    assert bool(res) is False


def test_find_template_region_restricts_and_offsets():
    scene = blank()
    tpl = make_template(color=(200, 0, 0), size=(20, 20))
    paste(scene, tpl, x=200, y=300)
    # Search only the bottom-right region; center must be reported in full coords.
    region = Rect(150, 250, 300, 400)
    res = vision.find_template(scene, tpl, threshold=0.9, region=region)
    assert res.found
    assert res.center.as_tuple() == (210, 310)


def test_find_all_templates_counts_instances():
    scene = blank()
    tpl = make_template(color=(0, 200, 0), size=(24, 24))
    for (x, y) in [(10, 10), (120, 10), (10, 200)]:
        paste(scene, tpl, x, y)
    hits = vision.find_all_templates(scene, tpl, threshold=0.9)
    assert len(hits) == 3


def test_find_color_and_count():
    scene = blank()
    # paint a red block (RGB 255,0,0 -> BGR 0,0,255)
    scene[50:70, 40:60] = (0, 0, 255)
    p = vision.find_color(scene, (255, 0, 0), tolerance=5)
    assert p is not None
    assert 40 <= p.x < 60 and 50 <= p.y < 70
    assert vision.count_color(scene, (255, 0, 0), tolerance=5) == 20 * 20


def test_get_pixel_rgb_order():
    scene = blank()
    scene[5, 5] = (10, 20, 30)  # BGR
    assert vision.get_pixel(scene, 5, 5) == (30, 20, 10)  # RGB


def test_match_multi_color():
    scene = blank(fill=0)
    scene[100, 100] = (0, 0, 255)   # anchor red
    scene[100, 110] = (0, 255, 0)   # +10x green
    scene[110, 100] = (255, 0, 0)   # +10y blue
    from autoauto.geometry import Point
    ok = vision.match_multi_color(
        scene, Point(100, 100), (255, 0, 0),
        offsets=[(10, 0, (0, 255, 0)), (0, 10, (0, 0, 255))], tolerance=3)
    assert ok is True
    bad = vision.match_multi_color(
        scene, Point(100, 100), (255, 0, 0),
        offsets=[(10, 0, (255, 255, 255))], tolerance=3)
    assert bad is False


def test_multiscale_finds_resized_template():
    scene = blank()
    base = make_template(color=(0, 180, 220), size=(40, 40))
    import cv2
    bigger = cv2.resize(base, None, fx=1.2, fy=1.2)
    paste(scene, bigger, x=90, y=90)
    res = vision.find_template_multiscale(scene, base, threshold=0.85)
    assert res.found
