"""Multi-device management and resilient calls.

`DeviceManager` enumerates and opens several devices (device farm / parallel
runs). `call_with_retries` wraps a flaky operation (transient adb drop) with
bounded retries and an optional recovery hook — the recovery hook is where a
caller reconnects the device before the next attempt.
"""
from __future__ import annotations

import time
from typing import Callable, TypeVar

from .device import AdbDevice
from .errors import DeviceError
from .logging_conf import get_logger

log = get_logger("devicemanager")

T = TypeVar("T")


class DeviceManager:
    def __init__(self) -> None:
        self._devices: dict[str, AdbDevice] = {}

    def list_serials(self) -> list[str]:
        return AdbDevice.list_serials()

    def open(self, serial: str | None = None) -> AdbDevice:
        dev = AdbDevice(serial).connect()
        self._devices[dev.serial] = dev
        return dev

    def open_all(self) -> list[AdbDevice]:
        return [self.open(s) for s in self.list_serials()]

    def get(self, serial: str) -> AdbDevice:
        if serial not in self._devices:
            raise DeviceError(f"device not opened: {serial}")
        return self._devices[serial]

    @property
    def serials(self) -> list[str]:
        return list(self._devices)


def call_with_retries(fn: Callable[[], T], attempts: int = 3,
                      delay: float = 1.0,
                      recover: Callable[[Exception], None] | None = None,
                      sleep: Callable[[float], None] = time.sleep,
                      exceptions: tuple[type[BaseException], ...] = (Exception,)) -> T:
    """Call `fn` with up to `attempts` tries.

    On a caught exception, run `recover(exc)` (e.g. reconnect) and retry after
    `delay`. Re-raises the last exception if all attempts fail.
    """
    last: BaseException | None = None
    for i in range(attempts):
        try:
            return fn()
        except exceptions as e:  # noqa: BLE001
            last = e
            log.warning("attempt %d/%d failed: %s", i + 1, attempts, e)
            if recover is not None:
                try:
                    recover(e)
                except Exception:  # pragma: no cover - recovery best-effort
                    log.exception("recover hook failed")
            if i < attempts - 1 and delay > 0:
                sleep(delay)
    assert last is not None
    raise last
