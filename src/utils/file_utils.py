"""Filesystem helpers: project-root discovery and atomic writes.

Infrastructure only - no gameplay logic.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_ROOT_MARKERS = ("pyproject.toml", "RULES.md")


def find_project_root(start: Path | None = None) -> Path:
    """Walk upwards from ``start`` until a project-root marker is found."""
    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if any((candidate / marker).exists() for marker in _ROOT_MARKERS):
            return candidate
    raise FileNotFoundError(
        "Project root not found (looked for pyproject.toml / RULES.md)."
    )


def ensure_dir(path: Path) -> Path:
    """Create the directory if needed and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text_atomic(path: Path, content: str) -> None:
    """Write text atomically: temp file in the same directory, then replace.

    A crash mid-write must never leave a truncated file behind. This matters
    for save files (RULES.md section 18: never silently invalidate saves).
    """
    ensure_dir(path.parent)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=path.name + ".", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
