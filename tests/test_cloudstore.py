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
