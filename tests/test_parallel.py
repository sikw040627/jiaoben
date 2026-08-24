import numpy as np

from autoauto.parallel import run_flow_on_each, run_jobs
from autoauto.report import RunReport
from autoauto.script_engine import Engine
from conftest import FakeClock, FakeDevice, make_template, paste


def test_run_jobs_maps_results():
    jobs = {"a": lambda: 1, "b": lambda: 2, "c": lambda: 3}
    out = run_jobs(jobs, max_workers=3)
    assert out == {"a": 1, "b": 2, "c": 3}


def test_run_jobs_captures_exceptions():
    def boom():
        raise ValueError("nope")

    out = run_jobs({"ok": lambda: 5, "bad": boom})
    assert out["ok"] == 5
    assert isinstance(out["bad"], ValueError)


def test_run_jobs_empty():
    assert run_jobs({}) == {}


def _engine_with_green():
    dev = FakeDevice()
    scene = np.full((dev._h, dev._w, 3), 30, dtype=np.uint8)
    tpl = make_template(color=(0, 200, 0), size=(40, 40))
    paste(scene, tpl, x=100, y=80)
    dev.frame = scene
    clk = FakeClock()
    return Engine(dev, randomize=False, clock=clk, sleep=clk.sleep), tpl, dev


def test_run_flow_on_each_runs_everywhere():
    e1, tpl, d1 = _engine_with_green()
    e2, _tpl2, d2 = _engine_with_green()
    engines = {"dev1": e1, "dev2": e2}
    steps = [{"op": "find_and_tap", "template": "g", "threshold": 0.9}]
    reports = run_flow_on_each(engines, steps, templates={"g": tpl}, max_workers=2)
    assert set(reports) == {"dev1", "dev2"}
    for label, rep in reports.items():
        assert isinstance(rep, RunReport)
        assert rep.success is True
    assert ("tap", 120, 100) in d1.calls
    assert ("tap", 120, 100) in d2.calls
