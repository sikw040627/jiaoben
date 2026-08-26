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


def test_index_page(server):
    import urllib.request
    HttpRemoteStore(server).put("daily", "#!/system/bin/sh\n# actions: 2\ninput tap 1 2\n")
    with urllib.request.urlopen(server + "/") as resp:
        assert resp.status == 200
        assert "text/html" in resp.headers.get("Content-Type", "")
        html = resp.read().decode("utf-8")
    assert "autoauto scripts" in html
    assert "daily" in html
    assert '/scripts/daily' in html


def test_index_requires_auth(auth_server):
    import urllib.error
    import urllib.request
    with pytest.raises(urllib.error.HTTPError) as ei:
        urllib.request.urlopen(auth_server + "/")
    assert ei.value.code == 401


def test_http_list_detailed(server):
    r = HttpRemoteStore(server)
    r.put("combo", "#!/system/bin/sh\n# actions: 2\ninput tap 1 2\n")
    rows = r.list_detailed()
    assert len(rows) == 1
    info = rows[0]
    assert info.name == "combo"
    assert info.actions == 2
    assert info.size > 0
    assert info.modified is not None          # file-backed server has mtime
    assert r.info("combo").name == "combo"


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
