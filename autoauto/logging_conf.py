"""Centralised logging configuration.

A single helper so every module logs with a consistent format and the app can
switch verbosity in one place. File logging is optional and lives under logs/.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

_CONFIGURED = False
_DEFAULT_FMT = "%(asctime)s %(levelname)-7s %(name)-18s %(message)s"


def setup_logging(level: int | str = logging.INFO,
                  logfile: str | Path | None = None,
                  fmt: str = _DEFAULT_FMT) -> None:
    """Configure the root 'autoauto' logger. Idempotent.

    :param level: logging level (int or name like "DEBUG").
    :param logfile: optional path; when given, logs are also written there.
    :param fmt: log line format.
    """
    global _CONFIGURED
    logger = logging.getLogger("autoauto")
    if isinstance(level, str):
        level = logging.getLevelName(level.upper())
    logger.setLevel(level)

    # Avoid duplicate handlers when called more than once.
    if _CONFIGURED:
        logger.setLevel(level)
        return

    formatter = logging.Formatter(fmt)

    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    if logfile is not None:
        logfile = Path(logfile)
        logfile.parent.mkdir(parents=True, exist_ok=True)
        fileh = logging.FileHandler(logfile, encoding="utf-8")
        fileh.setFormatter(formatter)
        logger.addHandler(fileh)

    logger.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the 'autoauto' namespace."""
    return logging.getLogger(f"autoauto.{name}")
