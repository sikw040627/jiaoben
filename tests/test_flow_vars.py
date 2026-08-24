import numpy as np

from autoauto.flow import Flow
from autoauto.script_engine import Engine
from conftest import FakeClock, make_template, paste


def make_engine(device):
    clk = FakeClock()
    return Engine(device, randomize=False, clock=clk, sleep=clk.sleep), clk


def green_scene(device, x=100, y=80):
    scene = np.full((device._h, device._w, 3), 30, dtype=np.uint8)
    tpl = make_template(color=(0, 200, 0), size=(40, 40))
    paste(scene, tpl, x=x, y=y)
    device.frame = scene
    return tpl


def test_set_incr_and_var_substitution(device, tmp_path):
    eng, _ = make_engine(device)
    steps = [
        {"op": "set", "name": "px", "value": 7},
        {"op": "incr", "name": "px", "by": 3},      # px -> 10
        {"op": "tap", "x": "$px", "y": "$px"},
    ]
    report = Flow(eng, archive_dir=str(tmp_path)).run(steps)
    assert report.success
    assert ("tap", 10, 10) in device.calls
    assert eng.ctx.get("px") == 10


def test_call_subflow(device, tmp_path):
    eng, _ = make_engine(device)
    subflows = {"claim": [{"op": "tap", "x": 1, "y": 1},
                          {"op": "tap", "x": 2, "y": 2}]}
    steps = [{"op": "call", "name": "claim"}, {"op": "call", "name": "claim"}]
    Flow(eng, subflows=subflows, archive_dir=str(tmp_path)).run(steps)
    taps = device.only("tap")
    assert taps.count(("tap", 1, 1)) == 2
    assert taps.count(("tap", 2, 2)) == 2


def test_call_unknown_subflow_fails(device, tmp_path):
    eng, _ = make_engine(device)
    report = Flow(eng, archive_dir=str(tmp_path)).run([{"op": "call", "name": "nope"}])
    assert report.success is False


def test_named_template_and_find_and_tap(device, tmp_path):
    tpl = green_scene(device)
    eng, _ = make_engine(device)
    steps = [{"op": "find_and_tap", "template": "start", "threshold": 0.9}]
    report = Flow(eng, templates={"start": tpl}, archive_dir=str(tmp_path)).run(steps)
    assert report.success
    assert ("tap", 120, 100) in device.calls


def test_while_image_bounded_by_max_iterations(device, tmp_path):
    tpl = green_scene(device)  # green stays present -> would loop forever
    eng, _ = make_engine(device)
    steps = [{"op": "while_image", "template": tpl, "threshold": 0.9,
              "max_iterations": 3, "interval": 0.1,
              "steps": [{"op": "tap", "x": 5, "y": 5}]}]
    Flow(eng, archive_dir=str(tmp_path)).run(steps)
    assert device.only("tap").count(("tap", 5, 5)) == 3


def test_find_color_tap(device, tmp_path):
    scene = np.zeros((device._h, device._w, 3), dtype=np.uint8)
    scene[200:220, 300:320] = (0, 0, 255)  # red block (RGB 255,0,0)
    device.frame = scene
    eng, _ = make_engine(device)
    steps = [{"op": "find_color_tap", "rgb": [255, 0, 0], "tolerance": 5}]
    report = Flow(eng, archive_dir=str(tmp_path)).run(steps)
    assert report.success
    _, tx, ty = device.only("tap")[0]
    assert 300 <= tx < 320 and 200 <= ty < 220
