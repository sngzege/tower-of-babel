"""Adapter isolation rule (developer decision, 2026-07-27).

pygame may only be imported inside src/rendering, src/input, and src/audio.
This test guards the rule automatically.
"""

from __future__ import annotations

from pathlib import Path

FORBIDDEN_DIRS = ("core", "gameplay", "world", "engine", "save", "ui", "debug", "utils")


def test_no_pygame_imports_outside_adapters() -> None:
    src = Path(__file__).resolve().parents[2] / "src"
    offenders: list[str] = []
    for dirname in FORBIDDEN_DIRS:
        package = src / dirname
        if not package.is_dir():
            continue
        for path in package.rglob("*.py"):
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            ):
                stripped = line.strip()
                if stripped.startswith("import pygame") or stripped.startswith(
                    "from pygame"
                ):
                    offenders.append(f"{path}:{lineno}")
    assert offenders == [], f"pygame imports outside adapters: {offenders}"
