"""Room encounter lifecycle: tracks combat room state.

A room encounter has three states:
  LOCKED   — player just entered, enemies spawning
  ACTIVE   — combat in progress
  CLEARED  — all required enemies dead, doors unlocked

The encounter manager tracks alive enemies and detects completion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EncounterState(Enum):
    LOCKED = "locked"
    ACTIVE = "active"
    CLEARED = "cleared"


@dataclass
class RoomEncounter:
    """Tracks the encounter in one room."""

    state: EncounterState = EncounterState.LOCKED
    total_enemies: int = 0
    alive_enemies: int = 0
    enemy_ids: list[str] = field(default_factory=list)

    def activate(self, enemy_count: int) -> None:
        """Start the encounter with N enemies."""
        self.state = EncounterState.ACTIVE
        self.total_enemies = enemy_count
        self.alive_enemies = enemy_count

    def on_enemy_died(self) -> None:
        """Mark one enemy as dead."""
        if self.state is not EncounterState.ACTIVE:
            return
        self.alive_enemies = max(0, self.alive_enemies - 1)
        if self.alive_enemies <= 0:
            self.state = EncounterState.CLEARED

    @property
    def cleared(self) -> bool:
        return self.state is EncounterState.CLEARED

    @property
    def active(self) -> bool:
        return self.state is EncounterState.ACTIVE

    @property
    def locked(self) -> bool:
        return self.state is EncounterState.LOCKED
