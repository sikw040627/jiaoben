"""Run work across multiple devices concurrently and aggregate results.

`run_jobs` is a small labelled thread pool. `run_flow_on_each` builds a Flow per
device and runs the same steps everywhere, returning {label: RunReport}.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, TypeVar

from .flow import Flow
from .logging_conf import get_logger
from .report import RunReport

log = get_logger("parallel")

T = TypeVar("T")


def run_jobs(jobs: dict[str, Callable[[], T]], max_workers: int | None = None,
             raise_errors: bool = False) -> dict[str, T | Exception]:
    """Run each labelled callable concurrently; return {label: result-or-exc}.

    With `raise_errors=False` (default) a failing job's exception is stored in
    the result map instead of propagating, so one bad device doesn't sink the
    whole batch.
    """
    results: dict[str, Any] = {}
    if not jobs:
        return results
    workers = max_workers or min(len(jobs), 16)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(fn): label for label, fn in jobs.items()}
        for fut in futures:
            label = futures[fut]
            try:
                results[label] = fut.result()
            except Exception as e:  # noqa: BLE001
                if raise_errors:
                    raise
                log.exception("job %s failed", label)
                results[label] = e
    return results


def run_flow_on_each(engines: dict[str, Any], steps: list[dict],
                     templates: dict[str, Any] | None = None,
                     subflows: dict[str, list[dict]] | None = None,
                     max_workers: int | None = None,
                     **flow_kwargs) -> dict[str, RunReport | Exception]:
    """Run the same task-flow `steps` on every engine, concurrently."""
    def make(engine) -> Callable[[], RunReport]:
        return lambda: Flow(engine, templates=templates, subflows=subflows,
                            **flow_kwargs).run(steps)

    jobs = {label: make(engine) for label, engine in engines.items()}
    return run_jobs(jobs, max_workers=max_workers)
