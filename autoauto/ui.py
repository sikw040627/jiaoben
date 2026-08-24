"""Control-tree automation via UiAutomator2 (optional).

Where find-image/find-color are pixel based, this drives the actual widget tree:
click by text / resource-id / xpath, wait for elements, read text, and perform
*continuous* multi-point gestures (finger stays down) which the plain ADB
`input` verbs cannot do.

uiautomator2 is imported lazily so the rest of the framework works even if it is
not installed. Initialising a controller requires a connected device.
"""
from __future__ import annotations

from typing import Any

from .geometry import Point
from .humanize import bezier_path
from .logging_conf import get_logger

log = get_logger("ui")


class UiController:
    def __init__(self, serial: str | None = None) -> None:
        import uiautomator2 as u2
        self._u2 = u2
        self.d = u2.connect(serial) if serial else u2.connect()
        log.info("uiautomator2 connected: %s", self.d.serial)

    # -- queries --------------------------------------------------------
    def exists(self, **selector: Any) -> bool:
        return self.d(**selector).exists

    def wait(self, timeout: float = 10.0, **selector: Any) -> bool:
        return self.d(**selector).wait(timeout=timeout)

    def text_of(self, **selector: Any) -> str:
        return self.d(**selector).get_text()

    def dump_hierarchy(self) -> str:
        return self.d.dump_hierarchy()

    # -- actions --------------------------------------------------------
    def click(self, **selector: Any) -> None:
        self.d(**selector).click()

    def click_xpath(self, xpath: str, timeout: float = 10.0) -> None:
        self.d.xpath(xpath).click(timeout=timeout)

    def set_text(self, value: str, **selector: Any) -> None:
        self.d(**selector).set_text(value)

    def gesture(self, points: list[Point], duration: float = 0.3) -> None:
        """Continuous multi-point gesture (finger never lifts)."""
        pts = [(p.x, p.y) for p in points]
        self.d.swipe_points(pts, duration)

    def curved_swipe(self, start: Point, end: Point, steps: int = 24,
                     duration: float = 0.3) -> None:
        """A single continuous swipe following a Bezier curve."""
        self.gesture(bezier_path(start, end, steps=steps), duration=duration)
