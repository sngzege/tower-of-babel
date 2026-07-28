"""Run lifecycle: manages the state and progression of a single run.

Run = one attempt from stage entry to death or boss victory.
The run owns seed, current stage/floor tracking, and the accumulated
temporary state (rewards, kills, currency).

This is designed to be extended by future persistent progression systems
without rewriting the core lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RunPhase(Enum):
    """High-level run lifecycle phases."""

    NOT_STARTED = "not_started"
    ACTIVE = "active"
    BOSS = "boss"
    VICTORY = "victory"
    DEATH = "death"
    COMPLETE = "complete"


@dataclass
class RunResult:
    """Immutable snapshot of run outcomes for meta-progression consumers."""

    victory: bool = False
    seed: int | str = 42
    depth_reached: int = 0
    floors_cleared: int = 0
    rooms_cleared: int = 0
    enemies_killed: int = 0
    gold_earned: int = 0


@dataclass
class RunState:
    """Mutable run state — discarded on run end."""

    phase: RunPhase = RunPhase.NOT_STARTED
    current_floor: int = 0
    current_room_index: int = 0
    rooms_cleared: int = 0
    enemies_killed: int = 0
    floor_enemies_remaining: int = 0
    rewards_collected: list[str] = field(default_factory=list)
    seed: int | str = 42


class RunManager:
    """Owns the run lifecycle. One instance per game session.

    Call order:
      manager.start(seed)    → NOT_STARTED → ACTIVE
      manager.on_room_clear() → increment rooms_cleared
      manager.on_enemy_kill() → increment kills
      manager.start_boss()    → ACTIVE → BOSS
      manager.on_victory()   → BOSS → VICTORY → COMPLETE
      manager.on_death()     → ACTIVE/any → DEATH → COMPLETE
      manager.reset()        → any → NOT_STARTED
    """

    def __init__(self) -> None:
        self.state = RunState()

    # -- Lifecycle --

    def start(self, seed: int | str = 42) -> None:
        """Begin a new run."""
        self.state = RunState(phase=RunPhase.ACTIVE, seed=seed)

    def start_boss(self) -> None:
        """Enter the boss floor."""
        self.state.phase = RunPhase.BOSS

    def on_victory(self) -> RunResult:
        """Complete the run with a boss victory."""
        self.state.phase = RunPhase.VICTORY
        return self._build_result(victory=True)

    def on_death(self) -> RunResult:
        """End the run with player death."""
        self.state.phase = RunPhase.DEATH
        return self._build_result(victory=False)

    # -- Progression --

    def on_room_clear(self) -> None:
        """Called when a room encounter completes."""
        self.state.rooms_cleared += 1

    def on_enemy_kill(self) -> None:
        """Called when an enemy dies."""
        self.state.enemies_killed += 1
        if self.state.floor_enemies_remaining > 0:
            self.state.floor_enemies_remaining -= 1

    def on_floor_advance(self) -> None:
        """Called when transitioning to the next floor."""
        self.state.current_floor += 1

    def can_restart(self) -> bool:
        return self.state.phase in (RunPhase.DEATH, RunPhase.VICTORY, RunPhase.COMPLETE)

    def reset(self) -> None:
        """Reset for a new run."""
        self.state = RunState()

    # -- Queries --

    def _build_result(self, victory: bool) -> RunResult:
        return RunResult(
            victory=victory,
            seed=self.state.seed,
            depth_reached=self.state.current_floor + 1,
            floors_cleared=self.state.current_floor,
            rooms_cleared=self.state.rooms_cleared,
            enemies_killed=self.state.enemies_killed,
        )

    @property
    def active(self) -> bool:
        return self.state.phase is RunPhase.ACTIVE

    @property
    def in_boss(self) -> bool:
        return self.state.phase is RunPhase.BOSS

    @property
    def ended(self) -> bool:
        return self.state.phase in (RunPhase.DEATH, RunPhase.VICTORY, RunPhase.COMPLETE)
