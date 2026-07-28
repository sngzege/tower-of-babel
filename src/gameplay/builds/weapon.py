"""Weapon system: data-driven weapon definitions that change attack behavior.

A weapon is a BuildComponent that determines:
  - Which AttackData to use for the primary attack
  - Tags for the weapon category (melee/ranged/sweep/thrust)
  - Base damage multiplier and speed multiplier
  - Which slot it occupies (weapon = exclusive equipment)

The weapon data comes from data/weapons/*.yaml files.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gameplay.builds.build_state import BuildComponent
from gameplay.combat.attack import AttackData


@dataclass(frozen=True)
class WeaponData(BuildComponent):
    """Data-driven weapon definition.

    ``attack_ref`` — id of the AttackData to use from data/combat/attacks/.
    ``damage_mult`` — multiplier applied on top of attack data's base damage.
    ``attack_speed_mult`` — multiplier on attack cooldown.
    ``tags`` — weapon category tags (melee, ranged, sweep, thrust, etc.).
    ``reach_mult`` — multiplier on attack hitbox reach.
    ``spread_mult`` — multiplier on attack hitbox spread.
    """
    attack_ref: str = "player_default_attack"
    damage_mult: float = 1.0
    attack_speed_mult: float = 1.0
    reach_mult: float = 1.0
    spread_mult: float = 1.0

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> WeaponData:
        """Build from a data/weapons/ YAML document."""
        return cls(
            id=str(document.get("id", "unknown")),
            name=str(document.get("name", "Unknown")),
            description=str(document.get("description", "")),
            tags=frozenset(document.get("tags", [])),
            attack_ref=str(document.get("attack_ref", "player_default_attack")),
            damage_mult=float(document.get("damage_mult", 1.0)),
            attack_speed_mult=float(document.get("attack_speed_mult", 1.0)),
            reach_mult=float(document.get("reach_mult", 1.0)),
            spread_mult=float(document.get("spread_mult", 1.0)),
        )

    def apply_to_attack(self, attack_data: AttackData) -> AttackData:
        """Apply weapon modifiers to base attack data.

        Returns a new AttackData with weapon modifiers applied.
        """
        from dataclasses import replace
        return replace(
            attack_data,
            damage=attack_data.damage * self.damage_mult,
            cooldown=attack_data.cooldown / self.attack_speed_mult,
            windup=attack_data.windup / self.attack_speed_mult,
            active=attack_data.active / self.attack_speed_mult,
            recovery=attack_data.recovery / self.attack_speed_mult,
            hitbox_spread=attack_data.hitbox_spread * self.spread_mult,
            hitbox_reach=attack_data.hitbox_reach * self.reach_mult,
        )
