from autoauto.scheduler import run_loop
from conftest import FakeClock


def test_run_loop_count():
    seen = []
    stats = run_loop(lambda i: seen.append(i), count=3, interval=0)
    assert seen == [0, 1, 2]
    assert stats.runs == 3
    assert stats.stopped_reason == "count"


def test_run_loop_until():
    calls = {"n": 0}

    def task(i):
        calls["n"] += 1

    stats = run_loop(task, until=lambda: calls["n"] >= 4, interval=0)
    # until() is checked BEFORE each run: stops the run after 4 executions.
    assert calls["n"] == 4
    assert stats.stopped_reason == "until"


def test_run_loop_timeout_with_fake_clock():
    clk = FakeClock()
    # Each run advances virtual time by 1s via the interval sleep.
    stats = run_loop(lambda i: None, interval=1.0, max_seconds=3.0,
                     clock=clk, sleep=clk.sleep)
    assert stats.stopped_reason == "timeout"
    assert stats.runs >= 3


def test_run_loop_counts_errors_and_continues():
    def task(i):
        if i in (1, 2):
            raise RuntimeError("boom")

    stats = run_loop(task, count=4, interval=0)
    assert stats.runs == 2       # i=0 and i=3 succeeded
    assert stats.errors == 2


def test_run_loop_stop_on_error():
    def task(i):
        if i == 1:
            raise RuntimeError("boom")

    stats = run_loop(task, count=5, interval=0, stop_on_error=True)
    assert stats.errors == 1
    assert stats.stopped_reason == "error"
    assert stats.runs == 1
