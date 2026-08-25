import pytest

from autoauto.cloudstore import (
    FileRemoteStore, MemoryRemoteStore, RemoteNotFound,
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
