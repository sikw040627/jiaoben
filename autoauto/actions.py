"""Action model for record & replay.

An automation session is a list of `Action` records with a relative timestamp.
Actions serialise to plain dicts/JSON so a recording can be saved to disk,
inspected, hand-edited, and replayed later — the same round-trip 自动精灵 offers
for its recorded scripts.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class Action:
    """A single input action at a relative time offset.

    :param kind: one of tap | long_press | swipe | key | text | wait.
    :param at_ms: milliseconds since the recording started.
    :param params: kind-specific payload (coordinates, keycode, text, ...).
    """
    kind: str
    at_ms: int
    params: dict[str, Any] = field(default_factory=dict)

    _KINDS = {"tap", "long_press", "swipe", "key", "text", "wait"}

    def __post_init__(self) -> None:
        if self.kind not in self._KINDS:
            raise ValueError(f"unknown action kind: {self.kind!r}")
        if self.at_ms < 0:
            raise ValueError("at_ms must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Action":
        return cls(kind=d["kind"], at_ms=int(d["at_ms"]),
                   params=dict(d.get("params", {})))


def save_actions(actions: list[Action], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"version": 1, "actions": [a.to_dict() for a in actions]}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_actions(path: str | Path) -> list[Action]:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError(f"unsupported recording version: {data.get('version')}")
    return [Action.from_dict(d) for d in data["actions"]]
