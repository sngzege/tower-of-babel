"""Structural definition of a save file.

A save is split into three parts (see docs/architecture/SAVE_SYSTEM.md):

- ``meta``: versioning and bookkeeping (always present).
- ``persistent``: everything that survives between runs (village, progression,
  unlocks, settings).
- ``run_state``: the in-progress run, or ``None`` when no run is active.

The split keeps design decisions D5 (death penalty), D4 (extraction), and D15
(mid-run save rules) open: run_state is optional and independently handled.
Infrastructure only - no gameplay fields are defined here.
"""

from __future__ import annotations

from typing import Any

from core.constants import SAVE_VERSION

REQUIRED_TOP_LEVEL_KEYS: tuple[str, ...] = ("meta", "persistent", "run_state")


def new_save_template() -> dict[str, Any]:
    """Empty, valid save structure. Content slots are filled by future systems."""
    return {
        "meta": {"save_version": SAVE_VERSION, "created_at": None, "updated_at": None},
        "persistent": {},
        "run_state": None,
    }


def validate_save_structure(save: object) -> list[str]:
    """Return a list of structural problems; an empty list means valid."""
    problems: list[str] = []
    if not isinstance(save, dict):
        return ["save root is not a mapping"]
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in save:
            problems.append(f"missing top-level key: '{key}'")
    meta = save.get("meta")
    if isinstance(meta, dict):
        if not isinstance(meta.get("save_version"), int):
            problems.append("meta.save_version is missing or not an int")
    else:
        problems.append("'meta' is not a mapping")
    if "persistent" in save and not isinstance(save["persistent"], dict):
        problems.append("'persistent' is not a mapping")
    if (
        "run_state" in save
        and save["run_state"] is not None
        and not isinstance(save["run_state"], dict)
    ):
        problems.append("'run_state' must be a mapping or null")
    return problems
