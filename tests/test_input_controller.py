import random

from autoauto.geometry import ResolutionAdapter
from autoauto.input_controller import InputController


def test_tap_exact_when_not_randomized(device):
    ic = InputController(device, randomize=False)
    ic.tap(100, 200, jitter=5)
    assert device.only("tap") == [("tap", 100, 200)]


def test_tap_jitter_within_radius(device):
    ic = InputController(device, rng=random.Random(2), randomize=True)
    for _ in range(50):
        device.calls.clear()
        ic.tap(100, 200, jitter=3)
        _, x, y = device.only("tap")[0]
        assert abs(x - 100) <= 3 and abs(y - 200) <= 3


def test_long_press_uses_zero_length_swipe(device):
    ic = InputController(device, randomize=False)
    ic.long_press(50, 60, duration_ms=700)
    assert device.only("swipe") == [("swipe", 50, 60, 50, 60, 700)]


def test_swipe_records(device):
    ic = InputController(device, randomize=False)
    ic.swipe(10, 20, 30, 40, duration_ms=250)
    assert device.only("swipe") == [("swipe", 10, 20, 30, 40, 250)]


def test_resolution_adapter_applied(device):
    # device is 1080x1920; script written for 540x960 -> 2x scale
    adapter = ResolutionAdapter(540, 960, 1080, 1920)
    ic = InputController(device, adapter=adapter, randomize=False)
    ic.tap(100, 100)
    assert device.only("tap") == [("tap", 200, 200)]


def test_scroll_direction(device):
    ic = InputController(device, randomize=False)
    ic.scroll("down", distance=500)
    # center is (540, 960); down = +y
    _, x1, y1, x2, y2, _ms = device.only("swipe")[0]
    assert (x1, y1) == (540, 960)
    assert x2 == 540 and y2 == 960 + 500


def test_keys_and_text(device):
    ic = InputController(device, randomize=False)
    ic.back(); ic.home(); ic.key("KEYCODE_ENTER"); ic.text("hi there")
    assert ("key", "KEYCODE_BACK") in device.calls
    assert ("key", "KEYCODE_HOME") in device.calls
    assert ("key", "KEYCODE_ENTER") in device.calls
    assert ("text", "hi there") in device.calls
