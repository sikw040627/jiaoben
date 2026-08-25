"""Remote (cloud) backends for replay scripts.

The local `ScriptStore` keeps `.sh` scripts on disk; a `RemoteStore` keeps them
somewhere shared so a recording made on one device can be downloaded and reused
on another — the "上传云端 -> 手机下载复用" loop.

`RemoteStore` is a tiny interface (put/get/list/delete/exists). Three
implementations ship here:

* `MemoryRemoteStore` — in-process dict; for tests and quick local use.
* `FileRemoteStore`   — file-backed (wraps `ScriptStore`); what the self-hosted
  server persists to.
* `HttpRemoteStore`   — client for the self-hosted HTTP server (`cloudserver`)
  or any endpoint speaking the same tiny REST shape. Pure stdlib `urllib`.

Object-storage backends (OSS/S3/COS) can implement the same interface later
without touching callers — see UNFINISHED.md.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from urllib.parse import quote

from .store import parse_action_count


@dataclass(frozen=True)
class RemoteInfo:
    """Metadata about a remotely stored script.

    `modified` is epoch seconds when the backend can supply it (file-backed),
    else None (e.g. the in-memory store keeps no timestamps).
    """
    name: str
    size: int              # utf-8 byte length of the script
    actions: int | None    # parsed from the `# actions: N` header
    modified: float | None

    def to_dict(self) -> dict:
        return {"name": self.name, "size": self.size,
                "actions": self.actions, "modified": self.modified}

    @classmethod
    def from_dict(cls, d: dict) -> "RemoteInfo":
        return cls(name=d["name"], size=int(d["size"]),
                   actions=d.get("actions"), modified=d.get("modified"))


def _info_from_content(name: str, content: str,
                       modified: float | None = None) -> RemoteInfo:
    return RemoteInfo(name=name, size=len(content.encode("utf-8")),
                      actions=parse_action_count(content), modified=modified)


class RemoteStoreError(Exception):
    """Transport or server error talking to a remote store."""


class RemoteNotFound(RemoteStoreError):
    """The requested script does not exist remotely."""


@runtime_checkable
class RemoteStore(Protocol):
    def put(self, name: str, content: str) -> None: ...
    def get(self, name: str) -> str: ...
    def list(self) -> list[str]: ...
    def delete(self, name: str) -> bool: ...
    def exists(self, name: str) -> bool: ...
    def rename(self, old: str, new: str) -> bool: ...
    def info(self, name: str) -> "RemoteInfo": ...
    def list_detailed(self) -> list["RemoteInfo"]: ...


def _rename_via_copy(store: "RemoteStore", old: str, new: str) -> bool:
    """Generic rename for stores without a native move: get -> put -> delete.

    Returns False if `old` does not exist. Raises if `new` already exists.
    """
    try:
        content = store.get(old)
    except RemoteNotFound:
        return False
    if store.exists(new):
        raise RemoteStoreError(f"target already exists: {new!r}")
    store.put(new, content)
    store.delete(old)
    return True


class MemoryRemoteStore:
    """In-memory RemoteStore (tests / local dev)."""

    def __init__(self) -> None:
        self._d: dict[str, str] = {}

    def put(self, name: str, content: str) -> None:
        self._d[str(name)] = content

    def get(self, name: str) -> str:
        try:
            return self._d[str(name)]
        except KeyError:
            raise RemoteNotFound(str(name)) from None

    def list(self) -> list[str]:
        return sorted(self._d)

    def delete(self, name: str) -> bool:
        return self._d.pop(str(name), None) is not None

    def exists(self, name: str) -> bool:
        return str(name) in self._d

    def rename(self, old: str, new: str) -> bool:
        return _rename_via_copy(self, old, new)

    def info(self, name: str) -> RemoteInfo:
        return _info_from_content(str(name), self.get(name))

    def list_detailed(self) -> list[RemoteInfo]:
        return [self.info(n) for n in self.list()]


class FileRemoteStore:
    """File-backed RemoteStore — the persistent backend for the self-host server."""

    def __init__(self, root) -> None:
        from .store import ScriptStore
        self._s = ScriptStore(root)

    def put(self, name: str, content: str) -> None:
        self._s.save(name, content)

    def get(self, name: str) -> str:
        if not self._s.exists(name):
            raise RemoteNotFound(str(name))
        return self._s.load(name)

    def list(self) -> list[str]:
        return self._s.list()

    def delete(self, name: str) -> bool:
        return self._s.delete(name)

    def exists(self, name: str) -> bool:
        return self._s.exists(name)

    def rename(self, old: str, new: str) -> bool:
        try:
            self._s.rename(old, new)
            return True
        except FileNotFoundError:
            return False
        except FileExistsError as e:
            raise RemoteStoreError(str(e)) from None

    def info(self, name: str) -> RemoteInfo:
        if not self._s.exists(name):
            raise RemoteNotFound(str(name))
        i = self._s.info(name)
        return RemoteInfo(name=i.name, size=i.size, actions=i.actions,
                          modified=i.modified)

    def list_detailed(self) -> list[RemoteInfo]:
        return [self.info(n) for n in self._s.list()]


class HttpRemoteStore:
    """RemoteStore client over HTTP (talks to `cloudserver`).

    :param base_url: e.g. ``http://192.168.1.10:8000``.
    :param token: optional bearer token (must match the server's).
    :param opener: injectable ``urlopen``-like callable, for tests.
    """

    def __init__(self, base_url: str, token: str | None = None,
                 opener=None, timeout: float = 10.0,
                 retries: int = 2, backoff: float = 0.3, sleep=None) -> None:
        self.base = base_url.rstrip("/")
        self.token = token
        self._open = opener or urllib.request.urlopen
        self.timeout = timeout
        self.retries = max(0, int(retries))
        self.backoff = backoff
        if sleep is None:
            import time
            sleep = time.sleep
        self._sleep = sleep

    def _request(self, method: str, path: str, data: str | None = None):
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        body = None
        if data is not None:
            body = data.encode("utf-8")
            headers["Content-Type"] = "text/x-shellscript; charset=utf-8"
        req = urllib.request.Request(self.base + path, data=body,
                                     method=method, headers=headers)
        attempt = 0
        while True:
            try:
                return self._open(req, timeout=self.timeout)
            except urllib.error.HTTPError as e:
                # A real HTTP response — a client/server status, never retried.
                if e.code == 404:
                    raise RemoteNotFound(path) from None
                raise RemoteStoreError(f"{method} {path} -> HTTP {e.code}") from e
            except urllib.error.URLError as e:
                # Transport failure (reset/refused/timeout) — retry with backoff.
                attempt += 1
                if attempt > self.retries:
                    raise RemoteStoreError(
                        f"{method} {path} failed after {attempt} attempt(s): "
                        f"{e.reason}") from e
                self._sleep(self.backoff * attempt)

    def put(self, name: str, content: str) -> None:
        with self._request("PUT", f"/scripts/{quote(str(name))}", content) as r:
            r.read()

    def get(self, name: str) -> str:
        with self._request("GET", f"/scripts/{quote(str(name))}") as r:
            return r.read().decode("utf-8")

    def list(self) -> list[str]:
        with self._request("GET", "/scripts") as r:
            return list(json.loads(r.read().decode("utf-8"))["scripts"])

    def delete(self, name: str) -> bool:
        try:
            with self._request("DELETE", f"/scripts/{quote(str(name))}") as r:
                r.read()
            return True
        except RemoteNotFound:
            return False

    def exists(self, name: str) -> bool:
        try:
            self.get(name)
            return True
        except RemoteNotFound:
            return False

    def rename(self, old: str, new: str) -> bool:
        # No dedicated endpoint; move client-side via get -> put -> delete.
        return _rename_via_copy(self, old, new)

    def list_detailed(self) -> list[RemoteInfo]:
        with self._request("GET", "/scripts?detail=1") as r:
            data = json.loads(r.read().decode("utf-8"))["scripts"]
        return [RemoteInfo.from_dict(d) for d in data]

    def info(self, name: str) -> RemoteInfo:
        # Reuse the detailed listing; fall back to content if absent.
        for i in self.list_detailed():
            if i.name == str(name):
                return i
        raise RemoteNotFound(str(name))
