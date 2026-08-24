import json

import cv2
import numpy as np

from autoauto.report import RunReport, StepResult, archive_frame


def test_run_report_counts_and_dict():
    r = RunReport(started_at=100.0, finished_at=101.5)
    r.add(StepResult(0, "tap", True))
    r.add(StepResult(1, "find_and_tap", False, "not found"))
    assert r.ok_count == 1
    assert r.fail_count == 1
    assert r.success is False
    d = r.to_dict()
    assert d["duration_ms"] == 1500
    assert d["ok"] == 1 and d["failed"] == 1
    assert len(d["steps"]) == 2


def test_run_report_save(tmp_path):
    r = RunReport(started_at=0.0, finished_at=1.0)
    r.add(StepResult(0, "sleep", True))
    f = tmp_path / "report.json"
    r.save(f)
    data = json.loads(f.read_text(encoding="utf-8"))
    assert data["success"] is True
    assert data["steps"][0]["op"] == "sleep"


def test_archive_frame_writes_png(tmp_path):
    frame = np.full((20, 20, 3), 128, dtype=np.uint8)
    path = archive_frame(frame, "step3/find:weird*name", out_dir=tmp_path)
    assert path.endswith(".png")
    img = cv2.imread(path)
    assert img is not None and img.shape == (20, 20, 3)
