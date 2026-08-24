"""Task scheduling: run a callable on an interval, N times, or until a condition.

Covers 自动精灵's "loop N times / run every X seconds / stop when ..." needs.
Clock and sleep are injectable so schedules unit-test instantly.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from .logging_conf import get_logger

log = get_logger("scheduler")


@dataclass
class RunStats:
    runs: int = 0
    errors: int = 0
    stopped_reason: str = ""


def run_loop(task: Callable[[int], None], *,
             count: int | None = None,
             interval: float = 0.0,
             max_seconds: float | None = None,
             until: Callable[[], bool] | None = None,
             stop_on_error: bool = False,
             clock: Callable[[], float] = time.monotonic,
             sleep: Callable[[float], None] = time.sleep) -> RunStats:
    """Repeatedly invoke `task(i)`.

    Stops when ANY limit trips: `count` reached, `max_seconds` elapsed, or
    `until()` returns True. `interval` is the delay *between* runs.

    :param stop_on_error: if True, an exception in `task` ends the loop;
        otherwise it is counted and the loop continues.
    """
    stats = RunStats()
    start = clock()
    i = 0
    while True:
        if count is not None and i >= count:
            stats.stopped_reason = "count"
            break
        if max_seconds is not None and (clock() - start) >= max_seconds:
            stats.stopped_reason = "timeout"
            break
        if until is not None and until():
            stats.stopped_reason = "until"
            break

        try:
            task(i)
            stats.runs += 1
        except Exception as e:  # noqa: BLE001 - loop resilience is the point
            stats.errors += 1
            log.exception("task run %d raised: %s", i, e)
            if stop_on_error:
                stats.stopped_reason = "error"
                break

        i += 1
        # Don't sleep after the final iteration when count-bounded.
        if count is not None and i >= count:
            stats.stopped_reason = "count"
            break
        if interval > 0:
            sleep(interval)
    return stats
