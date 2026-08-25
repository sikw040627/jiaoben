"""Command-line entry point:  python -m autoauto <command> [options]

Commands:
  devices                       list connected adb devices
  screencap <out.png>           save a screenshot
  tap <x> <y>                   tap a coordinate
  swipe <x1> <y1> <x2> <y2> [ms]  swipe
  findimage <template.png>      report best match (score + centre)
  record <out.json> [seconds]   record touches via getevent (needs a device)
  play <in.json> [loops]        replay a recording

Device-free commands (recording store & cloud sync):
  export-sh <in.json> <out.sh>  compile a JSON recording to an on-device .sh
  store list [--root D | --url U [--token T]]     local, or the remote catalog
  store show <name> [--root D]  print a stored script
  store info <name> [--root D]  print one script's metadata
  store rename <old> <new> [--root D] [--force]   rename a stored script
  serve [--root D --host H --port P --token T]   run the self-host cloud server
  push <name> --url U [--token T --root D]       upload one script to the cloud
  pull <name> --url U [--token T --root D]       download one script from cloud
  sync --url U [--token T --root D]              two-way sync local <-> cloud
"""
from __future__ import annotations

import argparse
import sys

from .logging_conf import setup_logging


def _fmt_modified(m) -> str:
    if m is None:
        return "-"
    from datetime import datetime
    return datetime.fromtimestamp(m).isoformat(timespec="seconds")


def _print_catalog(rows, remote: bool = False) -> None:
    """Print a name/size/actions/modified table for ScriptInfo or RemoteInfo."""
    if not rows:
        print("(empty)")
        return
    print(f"{'NAME':<24} {'SIZE':>7} {'ACTS':>5}  MODIFIED")
    for r in rows:
        acts = "-" if r.actions is None else str(r.actions)
        print(f"{r.name:<24} {r.size:>7} {acts:>5}  {_fmt_modified(r.modified)}")


def _run_deviceless(args) -> bool:
    """Handle commands that need no device. Return True if one was handled."""
    if args.cmd == "export-sh":
        from .shscript import convert_recording
        convert_recording(args.infile, args.out, keep_timing=not args.no_timing)
        print(f"compiled {args.infile} -> {args.out}")
        return True
    if args.cmd == "store":
        from .store import ScriptStore
        store = ScriptStore(args.root)
        if args.action == "list":
            if getattr(args, "url", None):        # remote catalog
                from .cloudstore import HttpRemoteStore
                rows = HttpRemoteStore(args.url, args.token).list_detailed()
                _print_catalog(rows, remote=True)
            else:
                _print_catalog(store.list_detailed(), remote=False)
        elif args.action == "info":
            if not args.name:
                print("store info needs a <name>"); return True
            i = store.info(args.name)
            print(f"name={i.name} size={i.size} actions={i.actions} "
                  f"modified={i.modified_iso()}")
        elif args.action == "rename":
            if not args.name or not args.new:
                print("store rename needs <old> <new>"); return True
            store.rename(args.name, args.new, overwrite=args.force)
            print(f"renamed {args.name} -> {args.new}")
        else:  # show
            if not args.name:
                print("store show needs a <name>"); return True
            print(store.load(args.name), end="")
        return True
    if args.cmd == "serve":
        from .cloudserver import serve
        serve(args.root, args.host, args.port, args.token)
        return True
    if args.cmd in ("push", "pull", "sync"):
        from .cloudstore import HttpRemoteStore
        from .store import ScriptStore
        from .sync import StoreSync
        s = StoreSync(ScriptStore(args.root), HttpRemoteStore(args.url, args.token))
        if args.cmd == "push":
            s.push(args.name); print(f"pushed {args.name} -> {args.url}")
        elif args.cmd == "pull":
            s.pull(args.name); print(f"pulled {args.name} <- {args.url}")
        else:
            res = s.sync()
            print(f"pushed: {res['pushed']}\npulled: {res['pulled']}")
        return True
    return False


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

    # --- device-free: store & cloud sync ---
    sp = sub.add_parser("export-sh"); sp.add_argument("infile"); sp.add_argument("out")
    sp.add_argument("--no-timing", action="store_true")
    sp = sub.add_parser("store")
    sp.add_argument("action", choices=["list", "show", "info", "rename"])
    sp.add_argument("name", nargs="?"); sp.add_argument("new", nargs="?")
    sp.add_argument("--root", default="store"); sp.add_argument("--force", action="store_true")
    sp.add_argument("--url", default=None, help="list the remote catalog instead of local")
    sp.add_argument("--token", default=None)
    sp = sub.add_parser("serve")
    sp.add_argument("--root", default="store"); sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8000); sp.add_argument("--token", default=None)
    for name in ("push", "pull"):
        sp = sub.add_parser(name); sp.add_argument("name")
        sp.add_argument("--url", required=True); sp.add_argument("--token", default=None)
        sp.add_argument("--root", default="store")
    sp = sub.add_parser("sync")
    sp.add_argument("--url", required=True); sp.add_argument("--token", default=None)
    sp.add_argument("--root", default="store")

    args = p.parse_args(argv)

    if _run_deviceless(args):
        return 0

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
