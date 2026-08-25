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
