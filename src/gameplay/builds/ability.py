"""Active ability system: data-driven abilities with cooldown and activation.

Abilities are active skills bound to Q/E/R slots. Each ability:
  - Has a cooldown timer
  - Has a mana/energy cost
  - Produces an effect on activation
  - Has tags for synergy

The ability executor manages the per-ability cooldown lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from gameplay.builds.build_state import BuildComponent


class AbilitySlot(Enum):
    SKILL_Q = "skill_q"
    SKILL_E = "skill_e"
    SKILL_R = "skill_r"


@dataclass(frozen=True)
class AbilityData(BuildComponent):
    """Data-driven ability definition.

    ``cooldown`` — seconds before the ability can be used again.
    ``mana_cost`` — mana/energy consumed on activation.
    ``effects`` — list of effect descriptors (interpreted by combat/build system).
    ``tags`` — ability category tags (offense, defense, mobility, etc.).
    """
    cooldown: float = 3.0
    mana_cost: float = 0.0
    effects: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> AbilityData:
        return cls(
            id=str(document.get("id", "unknown")),
            name=str(document.get("name", "Unknown")),
            description=str(document.get("description", "")),
            tags=frozenset(document.get("tags", [])),
            cooldown=float(document.get("cooldown", 3.0)),
            mana_cost=float(document.get("mana_cost", 0.0)),
            effects=tuple(document.get("effects", [])),
        )


@dataclass
class AbilityState:
    """Runtime state for one ability instance."""
    elapsed: float = 0.0
    ready: bool = True


class AbilityExecutor:
    """Manages one ability's cooldown lifecycle.

    Usage:
      executor = AbilityExecutor(ability_data)
      if executor.can_activate():
          executor.activate()
          # apply effects
      executor.update(dt)
    """

    def __init__(self, data: AbilityData) -> None:
        self.data = data
        self.state = AbilityState()

    def can_activate(self) -> bool:
        return self.state.ready

    def activate(self) -> bool:
        """Activate the ability if ready. Returns True on success."""
        if not self.state.ready:
            return False
        self.state = AbilityState(elapsed=0.0, ready=False)
        return True

    def update(self, dt: float) -> None:
        """Advance cooldown."""
        if not self.state.ready:
            self.state.elapsed += dt
            if self.state.elapsed >= self.data.cooldown:
                self.state.ready = True
                self.state.elapsed = 0.0
