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


def test_two_way_sync(tmp_path):
    local = _local(tmp_path)
    remote = MemoryRemoteStore()
    sync = StoreSync(local, remote)
    local.save("only_local", "l")
    remote.put("only_remote", "r")
    local.save("shared", "s"); remote.put("shared", "s")

    res = sync.sync()
    assert res == {"pushed": ["only_local"], "pulled": ["only_remote"]}
    # after sync both sides hold all three
    assert set(local.list()) == {"only_local", "only_remote", "shared"}
    assert set(remote.list()) == {"only_local", "only_remote", "shared"}
