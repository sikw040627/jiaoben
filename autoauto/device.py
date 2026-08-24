"""ADB device layer.

Thin wrapper over `adbutils` that exposes exactly the primitives the rest of the
framework needs: shell, screencap, screen size, and the raw input verbs
(tap/swipe/keyevent/text). Everything higher level (gestures, vision, scripts)
is built on top of this and can be unit-tested by swapping in a fake device.
"""
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from .errors import DeviceError, NoDeviceError
from .logging_conf import get_logger

log = get_logger("device")


@runtime_checkable
class DeviceProtocol(Protocol):
    """Structural interface used across the framework (real or fake)."""

    def shell(self, cmd: str, timeout: float | None = ...) -> str: ...
    def screencap_png(self) -> bytes: ...
    def window_size(self) -> tuple[int, int]: ...
    def tap(self, x: int, y: int) -> None: ...
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int) -> None: ...
    def keyevent(self, keycode: int | str) -> None: ...
    def input_text(self, text: str) -> None: ...


class AdbDevice:
    """Concrete device backed by adbutils."""

    def __init__(self, serial: Optional[str] = None) -> None:
        self.serial = serial
        self._dev = None  # lazily resolved adbutils device

    # -- connection -----------------------------------------------------
    @staticmethod
    def list_serials() -> list[str]:
        import adbutils
        return [d.serial for d in adbutils.adb.device_list()]

    def connect(self) -> "AdbDevice":
        import adbutils
        try:
            devices = adbutils.adb.device_list()
        except Exception as e:  # pragma: no cover - depends on adb server
            raise DeviceError(f"failed to reach adb server: {e}") from e
        if not devices:
            raise NoDeviceError("no adb devices connected (check `adb devices`)")
        if self.serial is None:
            self._dev = devices[0]
            self.serial = self._dev.serial
        else:
            self._dev = adbutils.adb.device(self.serial)
        log.info("connected to device %s", self.serial)
        return self

    @property
    def dev(self):
        if self._dev is None:
            self.connect()
        return self._dev

    # -- primitives -----------------------------------------------------
    def shell(self, cmd: str, timeout: float | None = 30.0) -> str:
        return self.dev.shell(cmd, timeout=timeout)

    def screencap_png(self) -> bytes:
        # adbutils returns a PIL.Image from .screenshot(); re-encode to PNG bytes
        import io
        img = self.dev.screenshot()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def window_size(self) -> tuple[int, int]:
        wsize = self.dev.window_size()
        return (int(wsize.width), int(wsize.height))

    def tap(self, x: int, y: int) -> None:
        self.dev.shell(f"input tap {int(x)} {int(y)}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int) -> None:
        self.dev.shell(
            f"input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {int(duration_ms)}")

    def keyevent(self, keycode: int | str) -> None:
        self.dev.shell(f"input keyevent {keycode}")

    def input_text(self, text: str) -> None:
        # Spaces must be escaped for `input text`.
        escaped = text.replace(" ", "%s")
        self.dev.shell(f"input text {escaped}")
