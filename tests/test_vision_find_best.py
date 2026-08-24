import numpy as np

from autoauto import vision
from conftest import make_template, paste


def test_find_best_exact_uses_high_threshold():
    scene = np.full((300, 300, 3), 30, dtype=np.uint8)
    tpl = make_template(color=(0, 200, 0), size=(40, 40))
    paste(scene, tpl, x=100, y=80)
    th, res = vision.find_best(scene, tpl, thresholds=(0.95, 0.9, 0.85))
    assert res.found
    assert th == 0.95
    assert res.center.as_tuple() == (120, 100)


def test_find_best_miss_returns_zero():
    scene = np.full((300, 300, 3), 30, dtype=np.uint8)
    absent = make_template(color=(0, 0, 200), size=(30, 30))
    th, res = vision.find_best(scene, absent, thresholds=(0.99, 0.95))
    assert th == 0.0
    assert res.found is False
