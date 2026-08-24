import pytest

from autoauto.actions import Action, load_actions, save_actions


def test_action_validation():
    with pytest.raises(ValueError):
        Action("frobnicate", 0)
    with pytest.raises(ValueError):
        Action("tap", -1)
    a = Action("tap", 10, {"x": 1, "y": 2})
    assert a.kind == "tap" and a.at_ms == 10


def test_action_dict_round_trip():
    a = Action("swipe", 250, {"x1": 1, "y1": 2, "x2": 3, "y2": 4, "duration_ms": 300})
    b = Action.from_dict(a.to_dict())
    assert b == a


def test_save_and_load(tmp_path):
    acts = [
        Action("tap", 0, {"x": 10, "y": 20}),
        Action("wait", 100, {"ms": 50}),
        Action("text", 200, {"s": "hello world"}),
    ]
    f = tmp_path / "rec.json"
    save_actions(acts, f)
    loaded = load_actions(f)
    assert loaded == acts


def test_load_rejects_bad_version(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text('{"version": 99, "actions": []}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_actions(f)
