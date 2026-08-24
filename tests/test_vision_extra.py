import numpy as np

from autoauto import vision
from autoauto.geometry import Rect
from conftest import make_template, paste


def blank(h=400, w=300, fill=30):
    return np.full((h, w, 3), fill, dtype=np.uint8)


def test_find_any_picks_present_template():
    scene = blank()
    green = make_template(color=(0, 200, 0), size=(40, 40))
    red = make_template(color=(0, 0, 200), size=(40, 40))
    paste(scene, green, x=100, y=100)
    name, res = vision.find_any(scene, {"green": green, "red": red}, threshold=0.9)
    assert name == "green"
    assert res.found and res.center.as_tuple() == (120, 120)


def test_find_any_miss_returns_none():
    scene = blank()
    red = make_template(color=(0, 0, 200), size=(40, 40))
    name, res = vision.find_any(scene, {"red": red}, threshold=0.98)
    assert name is None
    assert res.found is False


def test_color_ratio_full_and_half():
    scene = blank(h=100, w=100, fill=0)
    scene[:, :] = (0, 0, 255)  # entire region red (RGB 255,0,0)
    assert vision.color_ratio(scene, (255, 0, 0), tolerance=5) == 1.0

    half = blank(h=100, w=100, fill=0)
    half[:, :50] = (0, 0, 255)  # left half red
    r = vision.color_ratio(half, (255, 0, 0), tolerance=5)
    assert abs(r - 0.5) < 1e-6


def test_color_ratio_in_region():
    scene = blank(h=100, w=100, fill=0)
    scene[10:30, 10:30] = (0, 0, 255)  # a 20x20 red block
    region = Rect(10, 10, 30, 30)
    assert vision.color_ratio(scene, (255, 0, 0), tolerance=5, region=region) == 1.0


def test_find_color_hsv_red():
    scene = blank(h=80, w=80, fill=0)
    scene[20:40, 30:50] = (0, 0, 255)  # red
    p = vision.find_color_hsv(scene, (0, 100, 100), (10, 255, 255))
    assert p is not None
    assert 30 <= p.x < 50 and 20 <= p.y < 40


def test_find_template_masked_ignores_masked_pixels():
    scene = blank()
    tpl = make_template(color=(0, 180, 0), size=(40, 40))
    variant = tpl.copy()
    variant[0:8, 0:8] = (123, 45, 67)  # corrupt a corner
    paste(scene, variant, x=90, y=90)

    mask = np.full((40, 40), 255, dtype=np.uint8)
    mask[0:8, 0:8] = 0  # ignore the corrupted corner

    res = vision.find_template_masked(scene, tpl, mask, threshold=0.9)
    assert res.found
    assert res.center.as_tuple() == (110, 110)
