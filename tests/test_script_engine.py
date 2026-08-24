import numpy as np
import pytest

from autoauto.errors import TargetNotFoundError
from autoauto.script_engine import Context, Engine
from conftest import FakeClock, make_template, paste


def scene_with_green(device):
    scene = np.full((device._h, device._w, 3), 30, dtype=np.uint8)
    tpl = make_template(color=(0, 200, 0), size=(40, 40))
    paste(scene, tpl, x=100, y=80)
    device.frame = scene
    return tpl


def test_context_incr():
    c = Context(a=1)
    assert c.get("a") == 1
    assert c.incr("a") == 2
    assert c.incr("counter", by=5) == 5
    assert "counter" in c


def test_engine_find_image_and_tap(device):
    tpl = scene_with_green(device)
    eng = Engine(device, randomize=False)
    res = eng.find_image(tpl, threshold=0.9)
    assert res.found and res.center.as_tuple() == (120, 100)

    assert eng.find_and_tap(tpl, threshold=0.9) is True
    assert device.only("tap") == [("tap", 120, 100)]


def test_engine_find_and_tap_miss(device):
    eng = Engine(device, randomize=False)
    tpl = make_template(color=(0, 0, 255), size=(30, 30))  # not on the blank frame
    assert eng.find_and_tap(tpl, threshold=0.95) is False
    assert device.only("tap") == []


def test_wait_image_timeout_not_found(device):
    clk = FakeClock()
    eng = Engine(device, clock=clk, sleep=clk.sleep)
    tpl = make_template(color=(0, 0, 255), size=(30, 30))
    res = eng.wait_image(tpl, timeout=2.0, interval=0.5, threshold=0.99)
    assert res.found is False
    # virtual time advanced past the deadline
    assert clk.t >= 1002.0


def test_wait_image_required_raises(device):
    clk = FakeClock()
    eng = Engine(device, clock=clk, sleep=clk.sleep)
    tpl = make_template(color=(0, 0, 255), size=(30, 30))
    with pytest.raises(TargetNotFoundError):
        eng.wait_image(tpl, timeout=1.0, interval=0.5, threshold=0.99, required=True)


def test_wait_image_found_after_appears(device):
    clk = FakeClock()
    eng = Engine(device, clock=clk, sleep=clk.sleep)
    tpl = make_template(color=(0, 200, 0), size=(40, 40))

    calls = {"n": 0}
    original = eng.find_image

    def delayed(*a, **k):
        calls["n"] += 1
        if calls["n"] >= 3:            # appears on the 3rd poll
            scene_with_green(device)
        return original(*a, **k)

    eng.find_image = delayed
    res = eng.wait_image(tpl, timeout=5.0, interval=0.5, threshold=0.9)
    assert res.found is True
    assert calls["n"] >= 3


def test_wait_until_true_after_polls():
    clk = FakeClock()
    from autoauto.device import DeviceProtocol  # noqa: F401
    from conftest import FakeDevice
    eng = Engine(FakeDevice(), clock=clk, sleep=clk.sleep)
    state = {"n": 0}

    def pred():
        state["n"] += 1
        return state["n"] >= 4

    assert eng.wait_until(pred, timeout=10, interval=0.5) is True
    assert state["n"] == 4


def test_engine_find_color(device):
    scene = np.full((device._h, device._w, 3), 0, dtype=np.uint8)
    scene[10:30, 20:40] = (0, 0, 255)  # red block (RGB 255,0,0)
    device.frame = scene
    eng = Engine(device)
    p = eng.find_color((255, 0, 0), tolerance=5)
    assert p is not None and 20 <= p.x < 40
