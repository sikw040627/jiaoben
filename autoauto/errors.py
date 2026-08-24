"""Custom exceptions for the autoauto framework."""


class AutoAutoError(Exception):
    """Base class for all framework errors."""


class DeviceError(AutoAutoError):
    """ADB / device communication failure."""


class NoDeviceError(DeviceError):
    """No device is connected / selected."""


class TargetNotFoundError(AutoAutoError):
    """A vision/UI target (image, color, control) was not found in time."""


class OCRUnavailableError(AutoAutoError):
    """No OCR backend is installed/configured."""


class ScriptError(AutoAutoError):
    """Error raised from within a user script step."""
