"""Shared structural enumerations.

Framework-level vocabulary only. PROVISIONAL: the member sets are deliberately
broad enough to keep design decisions D4 (extraction rules) and D9 (ending
structure) open; unused members may be pruned once those decisions are locked.
"""

from __future__ import annotations

from enum import Enum


class SceneID(Enum):
    """Top-level application scenes (IMPLEMENTATION_PLAN scene system)."""

    BOOT = "boot"
    MAIN_MENU = "main_menu"
    VILLAGE = "village"
    DUNGEON = "dungeon"
    PAUSE = "pause"
    DEATH = "death"
    VICTORY = "victory"


class RunOutcome(Enum):
    """How a run ended. Supports both extraction and death-only models (D4)."""

    DIED = "died"
    EXTRACTED = "extracted"
    VICTORY = "victory"
    ABANDONED = "abandoned"
