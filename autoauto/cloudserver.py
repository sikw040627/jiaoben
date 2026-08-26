"""A minimal self-hosted cloud server for replay scripts (stdlib only).

Run it on any machine your phones can reach; recordings are uploaded here and
phones pull them back. It is the reference backend for `HttpRemoteStore` and
implements a tiny REST shape over a `RemoteStore`:

    GET    /                   -> a plain HTML catalog page (browse from a phone)
    GET    /scripts            -> {"scripts": ["daily", ...]}
    GET    /scripts?detail=1   -> {"scripts": [{"name","size","actions","modified"}, ...]}
    GET    /scripts/<name>     -> the raw .sh text (404 if missing)
    PUT    /scripts/<name>     -> body is the .sh text; stores it
    DELETE /scripts/<name>     -> deletes it (404 if missing)

Optional bearer-token auth: pass `token=...` and clients must send
`Authorization: Bearer <token>`.

Start from the CLI:  python -m autoauto serve --root store --port 8000
"""
from __future__ import annotations

import html
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlsplit

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
            m = _NAME_RE.match(urlsplit(self.path).path)
            return unquote(m.group(1)) if m else None

        def log_message(self, *args) -> None:  # keep the server quiet
            pass

        # -- verbs -----------------------------------------------------
        def _index_html(self) -> bytes:
            rows = store.list_detailed()
            items = []
            for i in rows:
                href = "/scripts/" + quote(i.name)
                acts = "-" if i.actions is None else i.actions
                items.append(
                    f'<li><a href="{html.escape(href)}">{html.escape(i.name)}</a>'
                    f' <small>{i.size} B, {acts} acts</small></li>')
            body = (
                "<!doctype html><meta charset=utf-8>"
                "<meta name=viewport content='width=device-width,initial-scale=1'>"
                "<title>autoauto scripts</title>"
                "<h1>autoauto scripts (%d)</h1><ul>%s</ul>"
                "<p><small>tap a script to download the .sh; run it on-device "
                "with <code>sh &lt;file&gt;</code>.</small></p>"
                % (len(rows), "".join(items) or "<li><em>(empty)</em></li>"))
            return body.encode("utf-8")

        def do_GET(self) -> None:
            if not self._authed():
                return self._send(401, b"unauthorized")
            split = urlsplit(self.path)
            if split.path in ("", "/"):
                return self._send(200, self._index_html(),
                                  "text/html; charset=utf-8")
            if split.path == "/scripts":
                if parse_qs(split.query).get("detail"):
                    scripts = [i.to_dict() for i in store.list_detailed()]
                else:
                    scripts = store.list()
                body = json.dumps({"scripts": scripts}).encode("utf-8")
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
