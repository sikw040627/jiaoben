"""Example: a small 'daily task' loop against a connected device.

Run (with a device connected and templates captured under assets/templates/):

    D:\\android-auto\\.venv\\Scripts\\python.exe scripts\\example_daily_task.py

It demonstrates the common pattern: wait for a screen, tap a button, handle a
popup if present, and repeat on a schedule with a stop condition.
"""
from __future__ import annotations

from autoauto import Auto, setup_logging
from autoauto.geometry import Rect
from autoauto.scheduler import run_loop


def main() -> None:
    setup_logging("INFO", logfile="logs/daily.log")
    auto = Auto().connect()
    eng = auto.engine

    def one_round(i: int) -> None:
        eng.frame(force=True)
        # 1) enter the activity if the start button is on screen
        if eng.find_and_tap("assets/templates/start.png", timeout=8):
            eng.ctx.incr("entered")
        # 2) dismiss a reward popup if it shows up
        eng.find_and_tap("assets/templates/close_popup.png", timeout=3)
        # 3) example colour check in a region (e.g. an 'energy full' indicator)
        top_bar = Rect(0, 0, 1080, 120)
        if eng.find_color((255, 215, 0), tolerance=20, region=top_bar):
            eng.ctx.incr("full_energy_rounds")

    stats = run_loop(one_round, count=5, interval=2.0)
    print("done:", stats)


if __name__ == "__main__":
    main()
