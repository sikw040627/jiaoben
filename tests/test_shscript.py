from autoauto.actions import Action
from autoauto.shscript import action_to_cmd, actions_to_sh, save_sh, convert_recording


def test_action_to_cmd_each_kind():
    assert action_to_cmd(Action("tap", 0, {"x": 10, "y": 20})) == "input tap 10 20"
    assert action_to_cmd(Action("swipe", 0, {"x1": 0, "y1": 0, "x2": 100, "y2": 50,
                                             "duration_ms": 200})) == "input swipe 0 0 100 50 200"
    assert action_to_cmd(Action("long_press", 0, {"x": 5, "y": 6,
                                                  "duration_ms": 800})) == "input swipe 5 6 5 6 800"
    assert action_to_cmd(Action("key", 0, {"keycode": "KEYCODE_BACK"})) == "input keyevent 'KEYCODE_BACK'"


def test_text_escapes_spaces_and_quotes():
    assert action_to_cmd(Action("text", 0, {"s": "hi there"})) == "input text 'hi%sthere'"
    # single quote in text is safely escaped for the shell
    assert action_to_cmd(Action("text", 0, {"s": "it's"})) == "input text 'it'\\''s'"


def test_wait_becomes_sleep():
    assert action_to_cmd(Action("wait", 0, {"ms": 500})) == "sleep 0.5"
    assert action_to_cmd(Action("wait", 0, {"ms": 0})) == "sleep 0"


def test_actions_to_sh_preserves_timing():
    actions = [Action("tap", 0, {"x": 1, "y": 2}),
               Action("tap", 750, {"x": 3, "y": 4})]
    sh = actions_to_sh(actions)
    lines = sh.strip().splitlines()
    assert lines[0] == "#!/system/bin/sh"
    body = [l for l in lines if not l.startswith("#") and l]
    # 0ms tap, then a 0.75s sleep, then the second tap
    assert body == ["input tap 1 2", "sleep 0.75", "input tap 3 4"]


def test_actions_to_sh_no_timing_and_no_header():
    actions = [Action("tap", 0, {"x": 1, "y": 2}),
               Action("tap", 750, {"x": 3, "y": 4})]
    sh = actions_to_sh(actions, header=False, keep_timing=False)
    assert sh == "input tap 1 2\ninput tap 3 4\n"


def test_save_and_convert_roundtrip(tmp_path):
    from autoauto.actions import save_actions
    actions = [Action("tap", 0, {"x": 1, "y": 2}), Action("wait", 100, {"ms": 100})]
    out = tmp_path / "rec.sh"
    save_sh(actions, out)
    assert out.read_text(encoding="utf-8").startswith("#!/system/bin/sh")

    j = tmp_path / "rec.json"
    save_actions(actions, j)
    out2 = tmp_path / "rec2.sh"
    convert_recording(j, out2)
    assert out2.read_text(encoding="utf-8") == out.read_text(encoding="utf-8")
