"""Command-line entry point:  python -m autoauto <command> [options]

Commands:
  devices                       list connected adb devices
  screencap <out.png>           save a screenshot
  tap <x> <y>                   tap a coordinate
  swipe <x1> <y1> <x2> <y2> [ms]  swipe
  findimage <template.png>      report best match (score + centre)
  record <out.json> [seconds]   record touches via getevent (needs a device)
  play <in.json> [loops]        replay a recording
"""
from __future__ import annotations

import argparse
import sys

from .logging_conf import setup_logging


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    p = argparse.ArgumentParser(prog="autoauto")
    p.add_argument("-s", "--serial", default=None, help="adb serial")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("devices")

    sp = sub.add_parser("screencap"); sp.add_argument("out")
    sp = sub.add_parser("tap"); sp.add_argument("x", type=int); sp.add_argument("y", type=int)
    sp = sub.add_parser("swipe")
    for a in ("x1", "y1", "x2", "y2"):
        sp.add_argument(a, type=int)
    sp.add_argument("ms", type=int, nargs="?", default=300)
    sp = sub.add_parser("findimage"); sp.add_argument("template")
    sp.add_argument("--threshold", type=float, default=0.85)
    sp = sub.add_parser("record"); sp.add_argument("out"); sp.add_argument("seconds", type=float, nargs="?", default=10)
    sp = sub.add_parser("play"); sp.add_argument("infile"); sp.add_argument("loops", type=int, nargs="?", default=1)

    args = p.parse_args(argv)

    from .device import AdbDevice

    if args.cmd == "devices":
        serials = AdbDevice.list_serials()
        print("\n".join(serials) if serials else "(no devices)")
        return 0

    dev = AdbDevice(args.serial).connect()

    if args.cmd == "screencap":
        with open(args.out, "wb") as f:
            f.write(dev.screencap_png())
        print(f"saved {args.out}")
    elif args.cmd == "tap":
        dev.tap(args.x, args.y); print("ok")
    elif args.cmd == "swipe":
        dev.swipe(args.x1, args.y1, args.x2, args.y2, args.ms); print("ok")
    elif args.cmd == "findimage":
        from .script_engine import Engine
        res = Engine(dev).find_image(args.template, threshold=args.threshold)
        print(f"found={res.found} score={res.score:.3f} center="
              f"{res.center.as_tuple() if res.center else None}")
    elif args.cmd == "record":
        from .actions import save_actions
        from .getevent import stream_getevent
        import time
        acts = []
        t0 = time.monotonic()
        print(f"recording {args.seconds}s ... touch the screen")
        for a in stream_getevent(dev.dev):
            acts.append(a)
            if time.monotonic() - t0 >= args.seconds:
                break
        save_actions(acts, args.out)
        print(f"saved {len(acts)} actions -> {args.out}")
    elif args.cmd == "play":
        from .recorder import Player
        from .input_controller import InputController
        n = Player(InputController(dev)).play_file(args.infile, loops=args.loops)
        print(f"dispatched {n} actions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
