from autoauto.input_controller import InputController
from autoauto.recorder import Player, Recorder
from conftest import FakeClock


def test_recorder_timestamps_with_fake_clock():
    clk = FakeClock()
    rec = Recorder(clock=clk).start()
    rec.tap(10, 20)          # t=0ms
    clk.advance(0.5)
    rec.swipe(0, 0, 100, 0)  # t=500ms
    clk.advance(0.25)
    rec.key("KEYCODE_BACK")  # t=750ms
    assert [a.at_ms for a in rec.actions] == [0, 500, 750]
    assert rec.actions[0].kind == "tap"


def test_recorder_wait_records_pause():
    clk = FakeClock()
    rec = Recorder(clock=clk).start()
    rec.tap(1, 2)
    w = rec.wait(250)
    assert w.kind == "wait"
    assert w.params == {"ms": 250}
    assert [a.kind for a in rec.actions] == ["tap", "wait"]


def test_recorder_trim_lead():
    clk = FakeClock()
    rec = Recorder(clock=clk).start()
    clk.advance(0.4)          # 400ms of dead lead-in before first touch
    rec.tap(1, 2)             # t=400ms
    clk.advance(0.3)
    rec.tap(3, 4)             # t=700ms
    rec.trim_lead()
    assert [a.at_ms for a in rec.actions] == [0, 300]


def test_recorder_save_and_player_replay(tmp_path, device):
    clk = FakeClock()
    rec = Recorder(clock=clk).start()
    rec.tap(10, 20)
    clk.advance(0.3)
    rec.swipe(0, 0, 100, 50, duration_ms=200)
    f = tmp_path / "r.json"
    rec.save(f)

    # Replay against the fake device; sleeps advance a fake clock instead of real.
    play_clock = FakeClock()
    ic = InputController(device, randomize=False)
    player = Player(ic, sleep=play_clock.sleep)
    n = player.play_file(f, loops=2)

    assert n == 4  # 2 actions x 2 loops
    taps = device.only("tap")
    swipes = device.only("swipe")
    assert taps == [("tap", 10, 20), ("tap", 10, 20)]
    assert swipes == [("swipe", 0, 0, 100, 50, 200)] * 2


def test_player_speed_and_timing():
    # Verify the replay waits the correct virtual gap between actions.
    from autoauto.actions import Action

    class RecordingController:
        def __init__(self):
            self.events = []

        def tap(self, x, y, **k):
            self.events.append(("tap", x, y))

        def swipe(self, *a, **k):
            self.events.append(("swipe", *a))

        def key(self, kc):
            self.events.append(("key", kc))

        def text(self, s):
            self.events.append(("text", s))

        def long_press(self, *a, **k):
            self.events.append(("lp", *a))

    slept = []
    ctrl = RecordingController()
    player = Player(ctrl, sleep=lambda dt: slept.append(dt), speed=2.0)
    actions = [Action("tap", 0, {"x": 1, "y": 1}),
               Action("tap", 1000, {"x": 2, "y": 2})]
    player.play(actions)
    # gap 1000ms at 2x speed -> 0.5s sleep
    assert slept == [0.5]
    assert ctrl.events == [("tap", 1, 1), ("tap", 2, 2)]
