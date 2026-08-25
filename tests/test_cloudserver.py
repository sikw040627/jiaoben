"""End-to-end: real threaded HTTP server + HttpRemoteStore over localhost."""
import threading

import pytest

from autoauto.cloudserver import make_server
from autoauto.cloudstore import HttpRemoteStore, RemoteNotFound, RemoteStoreError


@pytest.fixture
def server(tmp_path):
    httpd = make_server(root=tmp_path / "srv", host="127.0.0.1", port=0)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    host, port = httpd.server_address
    yield f"http://{host}:{port}"
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture
def auth_server(tmp_path):
    httpd = make_server(root=tmp_path / "srv", host="127.0.0.1", port=0, token="secret")
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    host, port = httpd.server_address
    yield f"http://{host}:{port}"
    httpd.shutdown()
    httpd.server_close()


def test_http_roundtrip(server):
    r = HttpRemoteStore(server)
    assert r.list() == []
    r.put("daily", "#!/system/bin/sh\ninput tap 1 2\n")
    assert r.exists("daily")
    assert r.get("daily") == "#!/system/bin/sh\ninput tap 1 2\n"
    assert r.list() == ["daily"]
    assert r.delete("daily") is True
    assert r.delete("daily") is False
    assert r.list() == []


def test_http_get_missing(server):
    r = HttpRemoteStore(server)
    with pytest.raises(RemoteNotFound):
        r.get("nope")


def test_http_rename(server):
    r = HttpRemoteStore(server)
    assert r.rename("ghost", "x") is False
    r.put("a", "input tap 1 2\n")
    assert r.rename("a", "b") is True
    assert not r.exists("a")
    assert r.get("b") == "input tap 1 2\n"


def test_auth_required(auth_server):
    bad = HttpRemoteStore(auth_server)  # no token
    with pytest.raises(RemoteStoreError):
        bad.list()
    good = HttpRemoteStore(auth_server, token="secret")
    good.put("a", "x")
    assert good.list() == ["a"]
