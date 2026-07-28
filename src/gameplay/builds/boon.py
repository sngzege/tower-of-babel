"""Run boon system: temporary build components acquired during a run.

Boons are the primary reward from room clears. They modify the build for
the current run and are discarded on death.

This replaces the previous RewardDefinition hardcoded pool with a
data-driven system that feeds into BuildState.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gameplay.builds.build_state import BuildComponent, BuildState


@dataclass(frozen=True)
class BoonData(BuildComponent):
    """A run boon: temporary build component from room rewards.

    ``effects`` — effects descriptors that BuildEffectApplier interprets.
      Format: [{ "stat": "damage", "value": 0.2, "is_percent": true }]
      or       [{ "stat": "damage", "tag": "melee", "value": 0.25, "is_percent": true }]
    """
    effects: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> BoonData:
        return cls(
            id=str(document.get("id", "unknown")),
            name=str(document.get("name", "Unknown")),
            description=str(document.get("description", "")),
            tags=frozenset(document.get("tags", [])),
            effects=tuple(document.get("effects", [])),
        )


def apply_boon_to_build(boon: BoonData, build: BuildState) -> None:
    """Apply a boon's effects to the build state.

    Updates cached modifier values on BuildState.
    """
    build.boon_ids.append(boon.id)

    for effect in boon.effects:
        stat = str(effect.get("stat", ""))
        value = float(effect.get("value", 0.0))
        is_percent = bool(effect.get("is_percent", False))
        tag = str(effect.get("tag", "")) if effect.get("tag") else ""

        if tag:
            # Tag-specific modifier.
            current = build._tag_mods.get((stat, tag), 0.0)
            if is_percent:
                build._tag_mods[(stat, tag)] = current + value
            else:
                build._tag_mods[(stat, tag)] = current + value
        else:
            # Global stat modifier.
            if stat == "damage":
                if is_percent:
                    build._damage_mult *= (1.0 + value)
                else:
                    build._damage_mult *= (1.0 + value / 100.0)
            elif stat == "move_speed":
                if is_percent:
                    build._move_speed_mult *= (1.0 + value)
                else:
                    build._move_speed_mult *= (1.0 + value / 100.0)
            elif stat == "attack_speed":
                if is_percent:
                    build._attack_speed_mult *= (1.0 + value)
                else:
                    build._attack_speed_mult *= (1.0 + value / 100.0)
            elif stat == "max_health":
                build._max_health_bonus += value
            elif stat == "dodge_charges":
                build._dodge_charge_bonus += int(value)
            elif stat == "crit_chance":
                build._crit_chance += value
            elif stat == "crit_damage":
                if is_percent:
                    build._crit_damage_mult *= (1.0 + value)
                else:
                    build._crit_damage_mult *= (1.0 + value / 100.0)


def apply_passive_to_build(passive_id: str, build: BuildState) -> None:
    """Register a passive in build state."""
    build.passive_ids.append(passive_id)


def apply_ability_to_build(ability_id: str, build: BuildState) -> None:
    """Register an ability in build state."""
    build.ability_ids.append(ability_id)
