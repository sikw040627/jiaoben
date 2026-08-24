import numpy as np

from autoauto.flow import Flow
from autoauto.script_engine import Engine
from conftest import FakeClock, make_template, paste


def green_scene(device, x=100, y=80):
    scene = np.full((device._h, device._w, 3), 30, dtype=np.uint8)
    tpl = make_template(color=(0, 200, 0), size=(40, 40))
    paste(scene, tpl, x=x, y=y)
    device.frame = scene
    return tpl


def make_engine(device):
    clk = FakeClock()
    return Engine(device, randomize=False, clock=clk, sleep=clk.sleep), clk


def test_flow_happy_path(device, tmp_path):
    tpl = green_scene(device)
    eng, _ = make_engine(device)
    steps = [
        {"op": "tap", "x": 10, "y": 20},
        {"op": "find_and_tap", "template": tpl, "threshold": 0.9},
        {"op": "assert_image", "template": tpl, "threshold": 0.9},
        {"op": "sleep", "seconds": 0.1},
    ]
    report = Flow(eng, archive_dir=str(tmp_path)).run(steps)
    assert report.success is True
    assert report.ok_count == 4
    assert ("tap", 10, 20) in device.calls
    assert ("tap", 120, 100) in device.calls  # centre of the pasted template


def test_flow_retries_then_fails_and_archives(device, tmp_path):
    green_scene(device)
    eng, clk = make_engine(device)
    absent = make_template(color=(0, 0, 255), size=(30, 30))
    steps = [{"op": "find_and_tap", "template": absent, "threshold": 0.99,
              "retries": 2, "retry_delay": 0.1}]
    report = Flow(eng, archive_dir=str(tmp_path)).run(steps)
    assert report.success is False
    assert report.fail_count == 1
    s = report.steps[0]
    assert s.ok is False
    assert s.screenshot is not None  # failure screenshot archived
    # retried twice -> clock advanced by 2 * 0.1
    assert clk.t >= 1000.2


def test_flow_abort_on_fail_stops(device, tmp_path):
    green_scene(device)
    eng, _ = make_engine(device)
    absent = make_template(color=(0, 0, 255), size=(30, 30))
    steps = [
        {"op": "assert_image", "template": absent, "threshold": 0.99,
         "on_fail": "abort"},
        {"op": "tap", "x": 1, "y": 1},  # must NOT run
    ]
    report = Flow(eng, archive_dir=str(tmp_path)).run(steps)
    assert report.fail_count == 1
    assert ("tap", 1, 1) not in device.calls


def test_flow_if_and_loop(device, tmp_path):
    tpl = green_scene(device)
    eng, _ = make_engine(device)
    steps = [
        {"op": "if_image", "template": tpl, "threshold": 0.9,
         "then": [{"op": "tap", "x": 1, "y": 1}],
         "else": [{"op": "tap", "x": 2, "y": 2}]},
        {"op": "loop", "times": 3, "steps": [{"op": "tap", "x": 5, "y": 5}]},
    ]
    Flow(eng, archive_dir=str(tmp_path)).run(steps)
    taps = device.only("tap")
    assert ("tap", 1, 1) in taps          # 'then' branch taken
    assert ("tap", 2, 2) not in taps
    assert taps.count(("tap", 5, 5)) == 3  # looped 3x


def test_flow_repeat_until_found_immediately(device, tmp_path):
    tpl = green_scene(device)
    eng, _ = make_engine(device)
    steps = [{"op": "repeat_until_image", "template": tpl, "threshold": 0.9,
              "timeout": 5, "do": [{"op": "tap", "x": 9, "y": 9}]}]
    report = Flow(eng, archive_dir=str(tmp_path)).run(steps)
    assert report.success is True
    assert ("tap", 9, 9) not in device.calls  # target present -> 'do' never ran


def test_flow_repeat_until_timeout_runs_do(device, tmp_path):
    green_scene(device)  # green present, but we wait for an ABSENT template
    eng, clk = make_engine(device)
    absent = make_template(color=(0, 0, 255), size=(30, 30))
    steps = [{"op": "repeat_until_image", "template": absent, "threshold": 0.99,
              "timeout": 2, "interval": 0.5,
              "do": [{"op": "tap", "x": 9, "y": 9}]}]
    report = Flow(eng, archive_dir=str(tmp_path)).run(steps)
    assert report.success is False
    assert ("tap", 9, 9) in device.calls  # 'do' ran while waiting
    assert clk.t >= 1002.0                  # advanced past the timeout
