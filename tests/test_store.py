import pytest

from autoauto.actions import Action
from autoauto.store import ScriptStore


def test_save_list_load_delete(tmp_path):
    store = ScriptStore(tmp_path / "store")
    p = store.save("daily", "input tap 1 2\n")
    assert p.name == "daily.sh"
    assert store.exists("daily")
    assert store.list() == ["daily"]
    assert store.load("daily") == "input tap 1 2\n"
    assert store.delete("daily") is True
    assert store.list() == []
    assert store.delete("daily") is False


def test_name_normalisation_and_suffix(tmp_path):
    store = ScriptStore(tmp_path)
    store.save("a", "x")
    store.save("b.sh", "y")
    assert store.exists("a") and store.exists("a.sh")
    assert sorted(store.list()) == ["a", "b"]


def test_save_actions_compiles_to_sh(tmp_path):
    store = ScriptStore(tmp_path)
    store.save_actions("combo", [Action("tap", 0, {"x": 5, "y": 6})])
    text = store.load("combo")
    assert "input tap 5 6" in text
    assert text.startswith("#!/system/bin/sh")


@pytest.mark.parametrize("bad", ["../evil", "sub/dir", "..", ".", ""])
def test_path_traversal_rejected(tmp_path, bad):
    store = ScriptStore(tmp_path)
    with pytest.raises(ValueError):
        store.path(bad)


def test_info_reports_size_and_actions(tmp_path):
    store = ScriptStore(tmp_path)
    store.save_actions("combo", [Action("tap", 0, {"x": 1, "y": 2}),
                                 Action("tap", 100, {"x": 3, "y": 4})])
    info = store.info("combo")
    assert info.name == "combo"
    assert info.size > 0
    assert info.actions == 2
    assert info.modified > 0
    assert "T" in info.modified_iso()


def test_info_actions_none_without_header(tmp_path):
    store = ScriptStore(tmp_path)
    store.save("raw", "input tap 1 2\n")   # no header banner
    assert store.info("raw").actions is None


def test_list_detailed(tmp_path):
    store = ScriptStore(tmp_path)
    store.save("b", "input tap 1 1\n")
    store.save("a", "input tap 2 2\n")
    rows = store.list_detailed()
    assert [r.name for r in rows] == ["a", "b"]   # sorted
    assert all(r.size > 0 for r in rows)


def test_rename(tmp_path):
    store = ScriptStore(tmp_path)
    store.save("old", "input tap 1 2\n")
    store.rename("old", "new")
    assert not store.exists("old")
    assert store.load("new") == "input tap 1 2\n"


def test_rename_missing_raises(tmp_path):
    store = ScriptStore(tmp_path)
    with pytest.raises(FileNotFoundError):
        store.rename("ghost", "x")


def test_rename_collision(tmp_path):
    store = ScriptStore(tmp_path)
    store.save("a", "1"); store.save("b", "2")
    with pytest.raises(FileExistsError):
        store.rename("a", "b")
    store.rename("a", "b", overwrite=True)
    assert store.load("b") == "1"
    assert not store.exists("a")
