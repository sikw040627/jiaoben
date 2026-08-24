import cv2
import numpy as np

from autoauto import stability
from autoauto.script_engine import Engine
from conftest import FakeClock, FakeDevice


def test_frame_diff_ratio_identical_and_half():
    a = np.zeros((100, 100, 3), dtype=np.uint8)
    assert stability.frame_diff_ratio(a, a.copy()) == 0.0

    b = a.copy()
    b[:, :50] = 255  # change left half
    assert abs(stability.frame_diff_ratio(a, b) - 0.5) < 1e-6


def test_frames_similar():
    a = np.full((50, 50, 3), 10, dtype=np.uint8)
    b = a.copy()
    b[0, 0] = (200, 200, 200)  # a single changed pixel
    assert stability.frames_similar(a, b, max_diff_ratio=0.01) is True
    c = a.copy()
    c[:, :] = 200
    assert stability.frames_similar(a, c, max_diff_ratio=0.01) is False


class SeqDevice(FakeDevice):
    """Device that returns a scripted sequence of frames (last repeats)."""

    def __init__(self, frames):
        super().__init__()
        self._frames = frames
        self._i = 0

    def screencap_png(self) -> bytes:
        frame = self._frames[min(self._i, len(self._frames) - 1)]
        self._i += 1
        ok, buf = cv2.imencode(".png", frame)
        assert ok
        return buf.tobytes()


def test_wait_until_stable_settles():
    A = np.zeros((60, 60, 3), dtype=np.uint8)
    B = np.full((60, 60, 3), 255, dtype=np.uint8)
    # first grab A (prev), then B (changing), then B, B (stable)
    dev = SeqDevice([A, B, B, B, B])
    clk = FakeClock()
    eng = Engine(dev, clock=clk, sleep=clk.sleep)
    assert stability.wait_until_stable(eng, timeout=10, interval=0.2,
                                       stable_frames=2) is True


def test_wait_until_stable_times_out_when_always_changing():
    frames = [np.full((40, 40, 3), v % 256, dtype=np.uint8)
              for v in range(0, 2000, 60)]
    dev = SeqDevice(frames)
    clk = FakeClock()
    eng = Engine(dev, clock=clk, sleep=clk.sleep)
    assert stability.wait_until_stable(eng, timeout=1.0, interval=0.2,
                                       stable_frames=2) is False


def test_restart_app_issues_shell_commands():
    dev = FakeDevice()
    stability.restart_app(dev, "com.example.game", activity=".MainActivity",
                          wait=0, sleep=lambda d: None)
    shells = [c[1] for c in dev.calls if c[0] == "shell"]
    assert any("am force-stop com.example.game" in s for s in shells)
    assert any("am start -n com.example.game/.MainActivity" in s for s in shells)
