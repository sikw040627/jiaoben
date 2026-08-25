"""Pluggable touch-injection backends.

The default injector uses `adb input`, which issues *discrete* tap/swipe events
— fine for UI automation, but it cannot do continuous or multi-finger gestures
(e.g. holding a joystick while tapping a skill). Continuous, multi-touch
injection with real device slots needs an on-device injector such as
**minitouch** or **MaaTouch** pushed to the device and driven over a socket
(often requiring root or an `app_process` launch).

That native-binary backend is intentionally left as a **placeholder**:
  * it needs a physical device plus a pushed native binary, so it cannot be
    built or exercised in this environment;
  * high-fidelity game-input replay edges on the project's declared scope
    boundary (see README/UNFINISHED), so it is not implemented here.

The interface is defined so a real backend can be dropped in later. The working
default is `AdbInputBackend`, which simply delegates to an existing
`InputController`.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TouchBackend(Protocol):
    def tap(self, x: int, y: int) -> None: ...
    def swipe(self, x1: int, y1: int, x2: int, y2: int,
              duration_ms: int = 300) -> None: ...


class AdbInputBackend:
    """Working default: delegate to an InputController (`adb input`)."""

    def __init__(self, controller) -> None:
        self._c = controller

    def tap(self, x: int, y: int) -> None:
        self._c.tap(x, y)

    def swipe(self, x1: int, y1: int, x2: int, y2: int,
              duration_ms: int = 300) -> None:
        self._c.swipe(x1, y1, x2, y2, duration_ms)


class MinitouchBackend:
    """PLACEHOLDER — continuous / multi-touch injection (minitouch / MaaTouch).

    Not implemented. Realising this backend requires pushing a native injector
    to the device and streaming events to it over a socket; see UNFINISHED.md
    (section: 游戏对局高保真录制). Constructing it fails loudly on purpose so no
    caller silently assumes multi-touch support that is not there.
    """

    def __init__(self, *args, **kwargs) -> None:
        raise NotImplementedError(
            "minitouch/MaaTouch continuous multi-touch backend is not "
            "implemented — see UNFINISHED.md. Use AdbInputBackend for now.")
