"""Declarative task-flow runner.

Describe a task as a list of step dicts (loadable from JSON/YAML) and run it.
Supports variables, sub-flow reuse, retries, assertions, conditionals and loops,
with automatic failure-screenshot archiving.

Variables
---------
* `{"op": "set", "name": "n", "value": 0}` / `{"op": "incr", "name": "n"}`
* Any scalar param equal to a string like `"$n"` is replaced by the value of
  context variable `n` at run time (e.g. `{"op": "tap", "x": "$px", "y": "$py"}`).

Named templates & sub-flows
---------------------------
* `templates={"start": <ndarray-or-path>}` lets steps say `"template": "start"`.
* `subflows={"claim": [ ...steps... ]}` lets a step say
  `{"op": "call", "name": "claim"}` to reuse a routine.

Control ops: `if_image`, `while_image`, `loop`, `repeat_until_image`.
Leaf ops: tap, swipe, key, text, sleep, set, incr, call, find_and_tap,
find_color_tap, wait_image, assert_image.
"""
from __future__ import annotations

from typing import Any

from .logging_conf import get_logger
from .report import RunReport, StepResult, archive_frame

log = get_logger("flow")

_CONTAINER_OPS = {"if_image", "while_image", "loop", "repeat_until_image", "call"}
_NESTED_KEYS = {"steps", "then", "else", "do"}


class Flow:
    def __init__(self, engine, templates: dict[str, Any] | None = None,
                 subflows: dict[str, list[dict]] | None = None,
                 archive_on_fail: bool = True,
                 archive_dir: str = "logs/failures",
                 max_iterations: int = 10000) -> None:
        self.engine = engine
        self.templates = templates or {}
        self.subflows = subflows or {}
        self.archive_on_fail = archive_on_fail
        self.archive_dir = archive_dir
        self.max_iterations = max_iterations
        self._idx = 0

    def run(self, steps: list[dict[str, Any]]) -> RunReport:
        report = RunReport(started_at=self.engine._clock())
        self._idx = 0
        self._run_steps(steps, report)
        report.finished_at = self.engine._clock()
        return report

    # -- variable / template resolution --------------------------------
    def _resolve_value(self, v):
        if isinstance(v, str) and v.startswith("$"):
            return self.engine.ctx.get(v[1:])
        return v

    def _resolved(self, step: dict) -> dict:
        """Return step with scalar params resolved against context vars.

        Nested step lists (steps/then/else/do) are left untouched.
        """
        out = {}
        for k, val in step.items():
            out[k] = val if k in _NESTED_KEYS else self._resolve_value(val)
        return out

    def _tpl(self, step: dict):
        t = step.get("template")
        # Only string names are looked up in the registry; ndarray/path pass through.
        if isinstance(t, str):
            return self.templates.get(t, t)
        return t

    # -- execution ------------------------------------------------------
    def _run_steps(self, steps: list[dict], report: RunReport) -> bool:
        for step in steps:
            if not self._run_step(step, report):
                if step.get("on_fail", "continue") == "abort":
                    return False
        return True

    def _run_step(self, step: dict, report: RunReport) -> bool:
        op = step.get("op")
        idx = self._idx
        self._idx += 1
        t0 = self.engine._clock()
        rstep = self._resolved(step)

        retries = int(rstep.get("retries", 0))
        delay = float(rstep.get("retry_delay", 0.5))
        ok, detail = False, ""
        try:
            for attempt in range(retries + 1):
                ok, detail = self._dispatch(op, rstep, step, report)
                if ok:
                    break
                if attempt < retries:
                    self.engine.sleep(delay)
        except Exception as e:  # noqa: BLE001
            ok, detail = False, f"exception: {e}"
            log.exception("step %d (%s) raised", idx, op)

        elapsed = int((self.engine._clock() - t0) * 1000)
        shot = None
        if not ok and self.archive_on_fail and op not in _CONTAINER_OPS:
            try:
                shot = archive_frame(self.engine.frame(force=True),
                                     f"step{idx}_{op}", self.archive_dir)
            except Exception:  # pragma: no cover - archiving is best-effort
                shot = None
        report.add(StepResult(idx, op or "?", ok, detail, elapsed, shot))
        return ok

    def _dispatch(self, op: str, s: dict, raw: dict,
                  report: RunReport) -> tuple[bool, str]:
        eng = self.engine
        # -- variables --
        if op == "set":
            eng.ctx.set(s["name"], s.get("value"))
            return True, f"{s['name']}={s.get('value')}"
        if op == "incr":
            newv = eng.ctx.incr(s["name"], int(s.get("by", 1)))
            return True, f"{s['name']}->{newv}"
        # -- raw input --
        if op == "tap":
            eng.input.tap(int(s["x"]), int(s["y"]), jitter=int(s.get("jitter", 2)))
            return True, ""
        if op == "swipe":
            eng.input.swipe(int(s["x1"]), int(s["y1"]), int(s["x2"]), int(s["y2"]),
                            duration_ms=int(s.get("ms", 300)))
            return True, ""
        if op == "key":
            eng.input.key(s["code"])
            return True, ""
        if op == "text":
            eng.input.text(str(s["s"]))
            return True, ""
        if op == "sleep":
            eng.sleep(float(s.get("seconds", 0)))
            return True, ""
        # -- vision-driven --
        if op == "find_and_tap":
            ok = eng.find_and_tap(self._tpl(s), timeout=float(s.get("timeout", 0)),
                                  threshold=float(s.get("threshold", 0.85)))
            return ok, "" if ok else "template not found"
        if op == "find_color_tap":
            p = eng.find_color(tuple(s["rgb"]), tolerance=int(s.get("tolerance", 12)),
                               region=s.get("region"))
            if p is None:
                return False, "colour not found"
            eng.input.tap(p.x, p.y, jitter=int(s.get("jitter", 2)))
            return True, ""
        if op == "wait_image":
            res = eng.wait_image(self._tpl(s), timeout=float(s.get("timeout", 10)),
                                 threshold=float(s.get("threshold", 0.85)),
                                 required=bool(s.get("required", False)))
            return res.found, "" if res.found else "image did not appear"
        if op == "assert_image":
            res = eng.find_image(self._tpl(s), threshold=float(s.get("threshold", 0.85)))
            return res.found, "" if res.found else "assertion failed: image absent"
        # -- control flow (use raw for nested step lists) --
        if op == "call":
            name = s["name"]
            if name not in self.subflows:
                return False, f"unknown subflow: {name}"
            self._run_steps(self.subflows[name], report)
            return True, f"called {name}"
        if op == "if_image":
            cond = eng.find_image(self._tpl(s),
                                  threshold=float(s.get("threshold", 0.85))).found
            self._run_steps(raw.get("then" if cond else "else", []), report)
            return True, f"branch={'then' if cond else 'else'}"
        if op == "loop":
            times = int(s.get("times", 1))
            for _ in range(times):
                if not self._run_steps(raw.get("steps", []), report):
                    break
            return True, f"looped {times}"
        if op == "while_image":
            interval = float(s.get("interval", 0.3))
            max_it = int(s.get("max_iterations", self.max_iterations))
            n = 0
            while n < max_it and eng.find_image(
                    self._tpl(s), threshold=float(s.get("threshold", 0.85))).found:
                if not self._run_steps(raw.get("steps", []), report):
                    break
                eng.sleep(interval)
                n += 1
            return True, f"while ran {n}x"
        if op == "repeat_until_image":
            timeout = float(s.get("timeout", 30))
            interval = float(s.get("interval", 0.5))
            deadline = eng._clock() + timeout
            found = False
            while eng._clock() < deadline:
                if eng.find_image(self._tpl(s),
                                  threshold=float(s.get("threshold", 0.85))).found:
                    found = True
                    break
                self._run_steps(raw.get("do", []), report)
                eng.sleep(interval)
            return found, "" if found else "target never appeared"
        return False, f"unknown op: {op}"
