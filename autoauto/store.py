"""Local file store for on-device replay scripts (`.sh`).

A recording compiles to a phone-runnable shell script (see `shscript.py`); this
store keeps those scripts as plain files under a directory in the project root
(default `store/`). It is the local-filesystem backend for the
record -> save -> list -> load -> reuse loop; a cloud/object-storage backend can
implement the same small surface later.

Deliberately minimal and dependency-free so it is trivially unit-testable with a
`tmp_path`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROOT = "store"
SUFFIX = ".sh"

_ACTIONS_RE = re.compile(r"^#\s*actions:\s*(\d+)", re.MULTILINE)


def parse_action_count(text: str) -> int | None:
    """Read the `# actions: N` banner a compiled script carries, if present."""
    m = _ACTIONS_RE.search(text)
    return int(m.group(1)) if m else None


@dataclass(frozen=True)
class ScriptInfo:
    """Metadata about one stored script (derived, no sidecar files)."""
    name: str
    size: int          # bytes on disk
    modified: float    # epoch seconds (filesystem mtime)
    actions: int | None  # parsed from the `# actions: N` header, if present

    def modified_iso(self) -> str:
        from datetime import datetime
        return datetime.fromtimestamp(self.modified).isoformat(timespec="seconds")


class ScriptStore:
    """Save / list / load `.sh` replay scripts under a single root directory."""

    def __init__(self, root: str | Path = DEFAULT_ROOT) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # -- path handling -------------------------------------------------
    def path(self, name: str) -> Path:
        """Resolve a flat script name to a path under the root.

        Names are flat (no nesting): any path separator or `.`/`..` is rejected
        rather than silently reinterpreted, so a name can never escape the root.
        """
        raw = str(name)
        if not raw or raw in {".", ".."} or "/" in raw or "\\" in raw:
            raise ValueError(f"invalid script name: {name!r}")
        base = raw if raw.endswith(SUFFIX) else raw + SUFFIX
        p = self.root / base
        if p.parent.resolve() != self.root.resolve():  # defence in depth
            raise ValueError(f"invalid script name: {name!r}")
        return p

    # -- write ---------------------------------------------------------
    def save(self, name: str, content: str) -> Path:
        """Store raw script text under `name`, return its path."""
        p = self.path(name)
        p.write_text(content, encoding="utf-8", newline="\n")
        return p

    def save_actions(self, name: str, actions, **kwargs) -> Path:
        """Compile a recording to `.sh` and store it under `name`."""
        from .shscript import actions_to_sh
        return self.save(name, actions_to_sh(actions, **kwargs))

    # -- read ----------------------------------------------------------
    def load(self, name: str) -> str:
        return self.path(name).read_text(encoding="utf-8")

    def exists(self, name: str) -> bool:
        return self.path(name).is_file()

    def list(self) -> list[str]:
        """Names of stored scripts (without the `.sh` suffix), sorted."""
        return sorted(p.stem for p in self.root.glob(f"*{SUFFIX}") if p.is_file())

    # -- metadata ------------------------------------------------------
    def info(self, name: str) -> ScriptInfo:
        """Size / modified-time / action-count for one script."""
        p = self.path(name)
        st = p.stat()  # raises FileNotFoundError if missing
        actions = parse_action_count(p.read_text(encoding="utf-8"))
        return ScriptInfo(name=p.stem, size=st.st_size, modified=st.st_mtime,
                          actions=actions)

    def list_detailed(self) -> list[ScriptInfo]:
        """`info` for every stored script, sorted by name."""
        return [self.info(n) for n in self.list()]

    # -- rename --------------------------------------------------------
    def rename(self, old: str, new: str, overwrite: bool = False) -> Path:
        """Rename a stored script. Raises if source missing or target exists
        (unless `overwrite`)."""
        src = self.path(old)
        dst = self.path(new)
        if not src.is_file():
            raise FileNotFoundError(f"no such script: {old!r}")
        if src.resolve() == dst.resolve():
            return dst
        if dst.exists() and not overwrite:
            raise FileExistsError(f"target already exists: {new!r}")
        src.replace(dst)  # atomic; overwrites dst if present
        return dst

    # -- delete --------------------------------------------------------
    def delete(self, name: str) -> bool:
        p = self.path(name)
        if p.is_file():
            p.unlink()
            return True
        return False
