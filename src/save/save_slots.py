"""Save slot management (Phase 14).

A slot is one save file (saves/save_N.yaml). SlotManager lists, selects, and
creates slots on top of the existing SaveManager. Slot semantics are kept
minimal: N slots, each independently writable/readable/deletable. The active
slot index is a caller concern (menu state), not persisted here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.constants import SAVES_DIR
from save.save_manager import SaveManager

DEFAULT_SLOT_COUNT = 3


def slot_path(saves_dir: Path, slot_index: int) -> Path:
    return saves_dir / f"save_{slot_index + 1}.yaml"


class SlotManager:
    """Manages a fixed set of save slots backed by SaveManager instances."""

    def __init__(
        self, saves_dir: Path | None = None, slot_count: int = DEFAULT_SLOT_COUNT
    ) -> None:
        self.saves_dir = saves_dir or SAVES_DIR
        self.slot_count = max(1, slot_count)
        self._managers: dict[int, SaveManager] = {}

    def manager(self, slot_index: int) -> SaveManager:
        """The SaveManager for a slot (0-based); raises on out-of-range."""
        if slot_index < 0 or slot_index >= self.slot_count:
            raise IndexError(
                f"slot {slot_index} out of range (0..{self.slot_count - 1})"
            )
        if slot_index not in self._managers:
            self._managers[slot_index] = SaveManager(
                path=slot_path(self.saves_dir, slot_index)
            )
        return self._managers[slot_index]

    def exists(self, slot_index: int) -> bool:
        return self.manager(slot_index).exists()

    def read(self, slot_index: int) -> dict[str, Any]:
        """Load a slot's save file (raises SaveError when missing/corrupt)."""
        return self.manager(slot_index).read()

    def read_or_new(self, slot_index: int) -> dict[str, Any]:
        return self.manager(slot_index).read_or_new()

    def write(self, slot_index: int, save: dict[str, Any]) -> None:
        self.manager(slot_index).write(save)

    def delete(self, slot_index: int) -> None:
        self.manager(slot_index).delete()

    def occupied_slots(self) -> list[int]:
        """Slots that currently have a save file."""
        return [
            index
            for index in range(self.slot_count)
            if self.manager(index).exists()
        ]
