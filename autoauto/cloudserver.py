"""A minimal self-hosted cloud server for replay scripts (stdlib only).

Run it on any machine your phones can reach; recordings are uploaded here and
phones pull them back. It is the reference backend for `HttpRemoteStore` and
implements a tiny REST shape over a `RemoteStore`:

    GET    /scripts            -> {"scripts": ["daily", ...]}
    GET    /scripts/<name>     -> the raw .sh text (404 if missing)
    PUT    /scripts/<name>     -> body is the .sh text; stores it
    DELETE /scripts/<name>     -> deletes it (404 if missing)

Optional bearer-token auth: pass `token=...` and clients must send
`Authorization: Bearer <token>`.

Start from the CLI:  python -m autoauto serve --root store --port 8000
"""
from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

from .cloudstore import FileRemoteStore, RemoteNotFound, RemoteStore

_NAME_RE = re.compile(r"^/scripts/([^/]+)$")


def make_handler(store: RemoteStore, token: str | None = None):
    class Handler(BaseHTTPRequestHandler):
        server_version = "autoauto-cloud/1.0"

        # -- helpers ---------------------------------------------------
        def _authed(self) -> bool:
            if not token:
                return True
            return self.headers.get("Authorization") == f"Bearer {token}"

        def _send(self, code: int, body: bytes = b"",
                  ctype: str = "text/plain; charset=utf-8") -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

        def _name(self):
            m = _NAME_RE.match(self.path)
            return unquote(m.group(1)) if m else None

        def log_message(self, *args) -> None:  # keep the server quiet
            pass

        # -- verbs -----------------------------------------------------
        def do_GET(self) -> None:
            if not self._authed():
                return self._send(401, b"unauthorized")
            if self.path == "/scripts":
                body = json.dumps({"scripts": store.list()}).encode("utf-8")
                return self._send(200, body, "application/json")
            name = self._name()
            if name is None:
                return self._send(404, b"not found")
            try:
                text = store.get(name)
            except RemoteNotFound:
                return self._send(404, b"not found")
            except ValueError:
                return self._send(400, b"bad name")
            return self._send(200, text.encode("utf-8"),
                              "text/x-shellscript; charset=utf-8")

        def do_PUT(self) -> None:
            if not self._authed():
                return self._send(401, b"unauthorized")
            name = self._name()
            if name is None:
                return self._send(404, b"not found")
            length = int(self.headers.get("Content-Length", 0))
            content = self.rfile.read(length).decode("utf-8")
            try:
                store.put(name, content)
            except ValueError:
                return self._send(400, b"bad name")
            return self._send(200, b"ok")

        def do_DELETE(self) -> None:
            if not self._authed():
                return self._send(401, b"unauthorized")
            name = self._name()
            if name is None:
                return self._send(404, b"not found")
            try:
                ok = store.delete(name)
            except ValueError:
                return self._send(400, b"bad name")
            return self._send(200 if ok else 404, b"ok" if ok else b"not found")

    return Handler


def make_server(root="store", host: str = "127.0.0.1", port: int = 8000,
                token: str | None = None, store: RemoteStore | None = None
                ) -> ThreadingHTTPServer:
    """Build (but do not start) a threaded server persisting to `root`.

    Pass `store` to serve a custom RemoteStore; otherwise a FileRemoteStore at
    `root` is used.
    """
    backend = store if store is not None else FileRemoteStore(root)
    return ThreadingHTTPServer((host, port), make_handler(backend, token))


def serve(root="store", host: str = "127.0.0.1", port: int = 8000,
          token: str | None = None) -> None:  # pragma: no cover - blocking loop
    httpd = make_server(root, host, port, token)
    print(f"autoauto cloud serving {root!r} on http://{host}:{port}  "
          f"(auth: {'on' if token else 'off'})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping ...")
    finally:
        httpd.server_close()
