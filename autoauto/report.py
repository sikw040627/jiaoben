"""Run reporting and failure-screenshot archiving.

A `RunReport` collects per-step outcomes so a task run produces an auditable
summary (counts, timings, failures). `archive_frame` dumps the current screen to
logs/ when something goes wrong, so failures are debuggable after the fact.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

import cv2

from .logging_conf import get_logger

log = get_logger("report")


@dataclass
class StepResult:
    index: int
    op: str
    ok: bool
    detail: str = ""
    elapsed_ms: int = 0
    screenshot: str | None = None


@dataclass
class RunReport:
    steps: list[StepResult] = field(default_factory=list)
    started_at: float = 0.0
    finished_at: float = 0.0

    def add(self, result: StepResult) -> None:
        self.steps.append(result)

    @property
    def ok_count(self) -> int:
        return sum(1 for s in self.steps if s.ok)

    @property
    def fail_count(self) -> int:
        return sum(1 for s in self.steps if not s.ok)

    @property
    def success(self) -> bool:
        return self.fail_count == 0

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "ok": self.ok_count,
            "failed": self.fail_count,
            "duration_ms": int((self.finished_at - self.started_at) * 1000),
            "steps": [asdict(s) for s in self.steps],
        }

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
                        encoding="utf-8")


def archive_frame(frame, name: str, out_dir: str | Path = "logs/failures") -> str:
    """Save a BGR frame to out_dir/<name>.png and return the path."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    # Sanitise the filename.
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
    path = out / f"{safe}.png"
    cv2.imwrite(str(path), frame)
    log.info("archived failure screenshot -> %s", path)
    return str(path)
