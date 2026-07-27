"""Central logging setup for the project.

Infrastructure only - no gameplay logic. Modules obtain loggers via
:func:`get_logger` so formatting and handlers stay consistent.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_root_configured = False


def setup_logging(level: str = "INFO", log_file: Path | None = None) -> None:
    """Configure the root logger once. Safe to call multiple times."""
    global _root_configured
    if _root_configured:
        return
    root = logging.getLogger()
    root.setLevel(level.upper())
    formatter = logging.Formatter(_DEFAULT_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    _root_configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module logger. Call :func:`setup_logging` once at bootstrap."""
    return logging.getLogger(name)
