"""autoauto — a legitimate Android UI-automation toolkit (自动精灵-style features).

Drives an Android device over ADB from the PC: screenshot, find-image,
find-color / multi-point colour, OCR, control-tree actions, tap/swipe/gesture,
record & replay, variables, waits, and scheduling.

Quick start (device connected via `adb devices`):

    from autoauto import Auto
    auto = Auto().connect()
    auto.engine.find_and_tap("assets/templates/start.png", timeout=10)

Everything is layered so each piece is usable and testable on its own.
"""
from __future__ import annotations

from .actions import Action, load_actions, save_actions
from .device import AdbDevice, DeviceProtocol
from .devicemanager import DeviceManager, call_with_retries
from .errors import (
    AutoAutoError, DeviceError, NoDeviceError,
    OCRUnavailableError, ScriptError, TargetNotFoundError,
)
from .flow import Flow
from .geometry import Point, Rect, ResolutionAdapter
from .input_controller import InputController
from .logging_conf import get_logger, setup_logging
from .numbers import parse_float, parse_int, read_float, read_int
from .ocr import preprocess_for_digits
from .parallel import run_flow_on_each, run_jobs
from .recorder import Player, Recorder
from .report import RunReport, StepResult, archive_frame
from .scheduler import RunStats, run_loop
from .script_engine import Context, Engine, load_template
from .cloudstore import (
    FileRemoteStore, HttpRemoteStore, MemoryRemoteStore,
    RemoteNotFound, RemoteStore, RemoteStoreError,
)
from .shscript import (
    action_to_cmd, actions_to_sh, convert_recording, save_sh,
)
from .stability import (
    force_stop, frame_diff_ratio, frames_similar, restart_app,
    start_app, wait_until_stable,
)
from .store import ScriptStore
from .sync import StoreSync
from .touch import AdbInputBackend, MinitouchBackend, TouchBackend
from .templateset import TemplateSet, scale_template
from .vision import MatchResult

__version__ = "0.1.0"

__all__ = [
    "Auto", "AdbDevice", "DeviceProtocol", "Engine", "Context",
    "InputController", "Recorder", "Player", "Action",
    "save_actions", "load_actions", "load_template",
    "Point", "Rect", "ResolutionAdapter", "MatchResult",
    "run_loop", "RunStats", "setup_logging", "get_logger",
    "Flow", "RunReport", "StepResult", "archive_frame",
    "DeviceManager", "call_with_retries",
    "wait_until_stable", "frame_diff_ratio", "frames_similar",
    "restart_app", "force_stop", "start_app",
    "parse_int", "parse_float", "read_int", "read_float",
    "preprocess_for_digits", "TemplateSet", "scale_template",
    "run_jobs", "run_flow_on_each",
    "actions_to_sh", "action_to_cmd", "save_sh", "convert_recording",
    "ScriptStore", "StoreSync",
    "RemoteStore", "MemoryRemoteStore", "FileRemoteStore", "HttpRemoteStore",
    "RemoteStoreError", "RemoteNotFound",
    "TouchBackend", "AdbInputBackend", "MinitouchBackend",
    "AutoAutoError", "DeviceError", "NoDeviceError",
    "TargetNotFoundError", "OCRUnavailableError", "ScriptError",
    "__version__",
]


class Auto:
    """Convenience facade wiring a device to an Engine (and lazy UI controller)."""

    def __init__(self, serial: str | None = None, randomize: bool = True) -> None:
        self.serial = serial
        self.randomize = randomize
        self.device: AdbDevice | None = None
        self.engine: Engine | None = None
        self._ui = None

    def connect(self) -> "Auto":
        self.device = AdbDevice(self.serial).connect()
        self.engine = Engine(self.device, randomize=self.randomize)
        return self

    @property
    def ui(self):
        """Lazily create the UiAutomator2 controller (needs the extra dep)."""
        if self._ui is None:
            from .ui import UiController
            self._ui = UiController(self.serial)
        return self._ui

    def recorder(self) -> Recorder:
        return Recorder()

    def player(self) -> Player:
        if self.engine is None:
            raise DeviceError("connect() first")
        return Player(self.engine.input)
