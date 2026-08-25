import pytest

from autoauto.cloudstore import (
    FileRemoteStore, MemoryRemoteStore, RemoteInfo, RemoteNotFound,
)


@pytest.mark.parametrize("make", [
    lambda tp: MemoryRemoteStore(),
    lambda tp: FileRemoteStore(tp / "remote"),
])
def test_remote_store_contract(make, tmp_path):
    r = make(tmp_path)
    assert r.list() == []
    assert r.exists("a") is False
    r.put("a", "input tap 1 2\n")
    assert r.exists("a") is True
    assert r.get("a") == "input tap 1 2\n"
    assert r.list() == ["a"]
    r.put("b", "input tap 3 4\n")
    assert r.list() == ["a", "b"]
    assert r.delete("a") is True
    assert r.delete("a") is False
    assert r.list() == ["b"]


@pytest.mark.parametrize("make", [
    lambda tp: MemoryRemoteStore(),
    lambda tp: FileRemoteStore(tp / "remote"),
])
def test_get_missing_raises(make, tmp_path):
    r = make(tmp_path)
    with pytest.raises(RemoteNotFound):
        r.get("nope")


@pytest.mark.parametrize("make", [
    lambda tp: MemoryRemoteStore(),
    lambda tp: FileRemoteStore(tp / "remote"),
])
def test_rename(make, tmp_path):
    from autoauto.cloudstore import RemoteStoreError
    r = make(tmp_path)
    assert r.rename("ghost", "x") is False       # missing source
    r.put("a", "input tap 1 2\n")
    assert r.rename("a", "b") is True
    assert not r.exists("a") and r.get("b") == "input tap 1 2\n"
    r.put("c", "z")
    with pytest.raises(RemoteStoreError):          # target exists
        r.rename("b", "c")


@pytest.mark.parametrize("make", [
    lambda tp: MemoryRemoteStore(),
    lambda tp: FileRemoteStore(tp / "remote"),
])
def test_info_and_list_detailed(make, tmp_path):
    r = make(tmp_path)
    r.put("combo", "#!/system/bin/sh\n# actions: 3\ninput tap 1 2\n")
    r.put("raw", "input tap 9 9\n")
    i = r.info("combo")
    assert isinstance(i, RemoteInfo)
    assert i.name == "combo" and i.actions == 3
    assert i.size == len("#!/system/bin/sh\n# actions: 3\ninput tap 1 2\n".encode())
    assert r.info("raw").actions is None
    rows = r.list_detailed()
    assert [x.name for x in rows] == ["combo", "raw"]


def test_remoteinfo_dict_roundtrip():
    i = RemoteInfo("a", 12, 2, 1000.0)
    assert RemoteInfo.from_dict(i.to_dict()) == i


# --- HttpRemoteStore transient-retry behaviour (injected opener + sleep) ---
import urllib.error

from autoauto.cloudstore import HttpRemoteStore, RemoteStoreError


class _FakeResp:
    def __init__(self, body=b"ok"):
        self._b = body
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return self._b


def test_retry_succeeds_after_transient_failures():
    calls = {"n": 0}
    slept = []

    def opener(req, timeout=None):
        calls["n"] += 1
        if calls["n"] <= 2:                      # fail twice, then succeed
            raise urllib.error.URLError("connection reset")
        return _FakeResp(b"body")

    r = HttpRemoteStore("http://h", opener=opener, retries=3,
                        backoff=0.5, sleep=slept.append)
    assert r.get("x") == "body"
    assert calls["n"] == 3
    assert slept == [0.5, 1.0]                    # backoff * attempt


def test_retry_exhausted_raises():
    slept = []

    def opener(req, timeout=None):
        raise urllib.error.URLError("refused")

    r = HttpRemoteStore("http://h", opener=opener, retries=2, sleep=slept.append)
    with pytest.raises(RemoteStoreError):
        r.get("x")
    assert len(slept) == 2                        # retried twice then gave up


def test_http_404_not_retried():
    calls = {"n": 0}

    def opener(req, timeout=None):
        calls["n"] += 1
        raise urllib.error.HTTPError(req.full_url, 404, "nf", {}, None)

    r = HttpRemoteStore("http://h", opener=opener, retries=5, sleep=lambda s: None)
    with pytest.raises(RemoteNotFound):
        r.get("x")
    assert calls["n"] == 1                        # 404 is terminal, no retry
