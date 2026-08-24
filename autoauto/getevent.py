"""Parse `adb shell getevent -lt` output into recordable actions.

This gives 自动精灵-style *live* recording without root: `adb shell getevent`
can read the touchscreen input device on most phones. We parse the timestamped,
labelled stream, reconstruct touch strokes (down -> moves -> up), and emit a
tap (short, little movement) or a swipe (longer path) per stroke.

The parser is intentionally pure (str lines in, Actions out) so it is fully unit
testable; `stream_getevent` is the thin device-facing loop around it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .actions import Action

# Example line (getevent -lt):
# [   12345.678901] /dev/input/event3 EV_ABS ABS_MT_POSITION_X 000004a1
_LINE = re.compile(
    r"\[\s*(?P<ts>\d+\.\d+)\]\s+\S+\s+(?P<type>\w+)\s+(?P<code>\w+)\s+(?P<value>\S+)")

TAP_MAX_MOVE = 16      # px total movement to still count as a tap
TAP_MAX_MS = 220       # stroke shorter than this + little move => tap


@dataclass
class _Stroke:
    start_ms: int
    points: list[tuple[int, int]] = field(default_factory=list)


def _to_int(hexval: str) -> int:
    return int(hexval, 16)


def parse_getevent(lines: list[str],
                   scale_x: float = 1.0, scale_y: float = 1.0) -> list[Action]:
    """Convert getevent lines into a timed list of tap/swipe Actions.

    :param scale_x/scale_y: multiply raw ABS values (digitizer units) to pixels.
        Many panels report touch coordinates already in pixels (scale 1.0); if
        not, pass screen_px / abs_max.
    """
    actions: list[Action] = []
    cur_x = cur_y = None
    touching = False
    stroke: _Stroke | None = None
    t0: float | None = None

    def now_ms(ts: float) -> int:
        nonlocal t0
        if t0 is None:
            t0 = ts
        return round((ts - t0) * 1000)

    for raw in lines:
        m = _LINE.search(raw)
        if not m:
            continue
        ts = float(m.group("ts"))
        code = m.group("code")
        val = m.group("value")

        if code == "ABS_MT_POSITION_X" or code == "ABS_X":
            cur_x = int(_to_int(val) * scale_x)
        elif code == "ABS_MT_POSITION_Y" or code == "ABS_Y":
            cur_y = int(_to_int(val) * scale_y)
        elif code == "BTN_TOUCH":
            if val.lower().endswith("down") or _safe_down(val):
                touching = True
                stroke = _Stroke(start_ms=now_ms(ts))
            else:  # UP
                touching = False
                if stroke is not None:
                    actions.append(_finish_stroke(stroke, now_ms(ts)))
                    stroke = None
        elif code == "ABS_MT_TRACKING_ID":
            # -1 (ffffffff) marks finger lift in protocol B
            if val.lower() == "ffffffff" and stroke is not None:
                touching = False
                actions.append(_finish_stroke(stroke, now_ms(ts)))
                stroke = None
            elif val.lower() != "ffffffff" and stroke is None:
                touching = True
                stroke = _Stroke(start_ms=now_ms(ts))
        elif code == "SYN_REPORT":
            if touching and stroke is not None and cur_x is not None and cur_y is not None:
                stroke.points.append((cur_x, cur_y))

    # Flush a stroke left open at end of stream.
    if stroke is not None and stroke.points:
        actions.append(_finish_stroke(stroke, stroke.start_ms))
    return [a for a in actions if a is not None]


def _safe_down(val: str) -> bool:
    try:
        return _to_int(val) == 1
    except ValueError:
        return False


def _finish_stroke(stroke: _Stroke, end_ms: int) -> Action | None:
    pts = stroke.points
    if not pts:
        return None
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    total_move = max(abs(px - x1) + abs(py - y1) for px, py in pts)
    dur = max(1, end_ms - stroke.start_ms)
    if total_move <= TAP_MAX_MOVE and dur <= TAP_MAX_MS:
        return Action("tap", stroke.start_ms, {"x": x1, "y": y1})
    if total_move <= TAP_MAX_MOVE:
        return Action("long_press", stroke.start_ms,
                      {"x": x1, "y": y1, "duration_ms": dur})
    return Action("swipe", stroke.start_ms,
                  {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration_ms": dur})


def stream_getevent(device, event_path: str | None = None,
                    scale_x: float = 1.0, scale_y: float = 1.0):  # pragma: no cover
    """Read a live getevent stream from a device and yield Actions.

    Device-facing (not unit tested). `device` must expose a `.shell` that can
    stream; typical use is with adbutils' streaming shell.
    """
    path = event_path or ""
    cmd = f"getevent -lt {path}".strip()
    buf: list[str] = []
    for line in device.shell(cmd, stream=True):
        buf.append(line)
        # Parse incrementally on SYN boundaries to keep latency low.
        if "SYN_REPORT" in line:
            acts = parse_getevent(buf, scale_x, scale_y)
            if acts:
                for a in acts:
                    yield a
                buf.clear()
