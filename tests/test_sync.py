from autoauto.cloudstore import MemoryRemoteStore
from autoauto.store import ScriptStore
from autoauto.sync import StoreSync


def _local(tmp_path):
    s = ScriptStore(tmp_path / "local")
    return s


def test_push_and_pull(tmp_path):
    local = _local(tmp_path)
    remote = MemoryRemoteStore()
    sync = StoreSync(local, remote)

    local.save("a", "input tap 1 2\n")
    sync.push("a")
    assert remote.get("a") == "input tap 1 2\n"

    remote.put("b", "input tap 9 9\n")
    sync.pull("b")
    assert local.load("b") == "input tap 9 9\n"


def test_push_all_pull_all(tmp_path):
    local = _local(tmp_path)
    remote = MemoryRemoteStore()
    sync = StoreSync(local, remote)
    local.save("x", "x"); local.save("y", "y")
    assert sorted(sync.push_all()) == ["x", "y"]
    assert remote.list() == ["x", "y"]

    remote.put("z", "z")
    got = sync.pull_all()
    assert "z" in got
    assert local.exists("z")


def test_rename_both_ends(tmp_path):
    local = _local(tmp_path)
    remote = MemoryRemoteStore()
    sync = StoreSync(local, remote)
    local.save("old", "content\n"); remote.put("old", "content\n")
    res = sync.rename("old", "new")
    assert res == {"local": True, "remote": True}
    assert local.exists("new") and not local.exists("old")
    assert remote.exists("new") and not remote.exists("old")


def test_rename_local_only(tmp_path):
    local = _local(tmp_path)
    remote = MemoryRemoteStore()
    sync = StoreSync(local, remote)
    local.save("old", "c")
    res = sync.rename("old", "new")
    assert res == {"local": True, "remote": False}
    assert local.exists("new")


def test_two_way_sync(tmp_path):
    local = _local(tmp_path)
    remote = MemoryRemoteStore()
    sync = StoreSync(local, remote)
    local.save("only_local", "l")
    remote.put("only_remote", "r")
    local.save("shared", "s"); remote.put("shared", "s")

    res = sync.sync()
    assert res == {"pushed": ["only_local"], "pulled": ["only_remote"], "updated": []}
    # after sync both sides hold all three
    assert set(local.list()) == {"only_local", "only_remote", "shared"}
    assert set(remote.list()) == {"only_local", "only_remote", "shared"}


def test_sync_policy_local_overwrites_remote(tmp_path):
    local = _local(tmp_path)
    remote = MemoryRemoteStore()
    sync = StoreSync(local, remote)
    local.save("shared", "LOCAL"); remote.put("shared", "REMOTE")
    res = sync.sync(policy="local")
    assert res["updated"] == ["shared"]
    assert remote.get("shared") == "LOCAL"


def test_sync_policy_remote_overwrites_local(tmp_path):
    local = _local(tmp_path)
    remote = MemoryRemoteStore()
    sync = StoreSync(local, remote)
    local.save("shared", "LOCAL"); remote.put("shared", "REMOTE")
    res = sync.sync(policy="remote")
    assert res["updated"] == ["shared"]
    assert local.load("shared") == "REMOTE"


def test_sync_policy_skip_leaves_conflicts(tmp_path):
    local = _local(tmp_path)
    remote = MemoryRemoteStore()
    sync = StoreSync(local, remote)
    local.save("shared", "LOCAL"); remote.put("shared", "REMOTE")
    res = sync.sync()  # default skip
    assert res["updated"] == []
    assert local.load("shared") == "LOCAL" and remote.get("shared") == "REMOTE"


def test_sync_bad_policy(tmp_path):
    import pytest
    sync = StoreSync(_local(tmp_path), MemoryRemoteStore())
    with pytest.raises(ValueError):
        sync.sync(policy="nope")
