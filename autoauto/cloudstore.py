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
from typing import Protocol, runtime_checkable
from urllib.parse import quote


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


class HttpRemoteStore:
    """RemoteStore client over HTTP (talks to `cloudserver`).

    :param base_url: e.g. ``http://192.168.1.10:8000``.
    :param token: optional bearer token (must match the server's).
    :param opener: injectable ``urlopen``-like callable, for tests.
    """

    def __init__(self, base_url: str, token: str | None = None,
                 opener=None, timeout: float = 10.0) -> None:
        self.base = base_url.rstrip("/")
        self.token = token
        self._open = opener or urllib.request.urlopen
        self.timeout = timeout

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
        try:
            return self._open(req, timeout=self.timeout)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise RemoteNotFound(path) from None
            raise RemoteStoreError(f"{method} {path} -> HTTP {e.code}") from e
        except urllib.error.URLError as e:
            raise RemoteStoreError(f"{method} {path} failed: {e.reason}") from e

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
