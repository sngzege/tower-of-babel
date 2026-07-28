"""Build state: authoritative representation of the player's current run build.

The BuildState is the single source of truth for what the player has equipped
and what effects are active. It is owned by the run lifecycle, not by Player.

BuildState is reset on run start and discarded on run end.

Components:
  - weapon: determines attack behavior
  - abilities: active skills (Q/E/R/T)
  - passives: persistent modifiers (from class/items)
  - boons: temporary run buffs (from rewards)
  - weapon_upgrades: run-time weapon modifications
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# -- Tag system --

WEAPON_TAGS = frozenset({
    "melee", "ranged", "sweep", "thrust", "projectile", "piercing",
})
ATTACK_TAGS = frozenset({
    "physical", "magical", "fire", "lightning", "bleed",
})
BOON_TAGS = frozenset({
    "offense", "defense", "mobility", "utility",
    "melee", "ranged", "projectile", "sweep", "piercing",
})


@dataclass(frozen=True)
class StatModifier:
    """A single numeric modifier to a player stat."""
    stat: str
    value: float
    is_percent: bool = False
    source: str = ""
    tags: frozenset[str] = frozenset()
    condition: str = ""


@dataclass(frozen=True)
class BuildComponent:
    """Base metadata for any piece of a build."""
    id: str
    name: str
    description: str = ""
    tags: frozenset[str] = frozenset()


@dataclass(frozen=False)
class BuildState:
    """Authoritative run build. Mutable during run, discarded on death."""

    weapon_id: str = "unarmed"
    ability_ids: list[str] = field(default_factory=list)
    passive_ids: list[str] = field(default_factory=list)
    boon_ids: list[str] = field(default_factory=list)
    weapon_upgrades: dict[str, float] = field(default_factory=dict)

    # Cached modifiers — recompute after changes.
    _damage_mult: float = 1.0
    _move_speed_mult: float = 1.0
    _attack_speed_mult: float = 1.0
    _max_health_bonus: float = 0.0
    _dodge_charge_bonus: int = 0
    _crit_chance: float = 0.0
    _crit_damage_mult: float = 1.5
    _tag_mods: dict[tuple[str, str], float] = field(default_factory=dict)
    _conditional_mods: list[dict] = field(default_factory=list)
    # Track whether Fury is currently active for toggling.
    _fury_active: bool = False

    def reset(self) -> None:
        """Clear all build components (new run)."""
        self.weapon_id = "unarmed"
        self.ability_ids.clear()
        self.passive_ids.clear()
        self.boon_ids.clear()
        self.weapon_upgrades.clear()
        self._damage_mult = 1.0
        self._move_speed_mult = 1.0
        self._attack_speed_mult = 1.0
        self._max_health_bonus = 0.0
        self._dodge_charge_bonus = 0
        self._crit_chance = 0.0
        self._crit_damage_mult = 1.5
        self._tag_mods.clear()
        self._conditional_mods.clear()
        self._fury_active = False

    @property
    def damage_mult(self) -> float: return self._damage_mult

    @property
    def move_speed_mult(self) -> float: return self._move_speed_mult

    @property
    def attack_speed_mult(self) -> float: return self._attack_speed_mult

    @property
    def max_health_bonus(self) -> float: return self._max_health_bonus

    @property
    def dodge_charge_bonus(self) -> int: return self._dodge_charge_bonus

    @property
    def crit_chance(self) -> float: return self._crit_chance

    @property
    def crit_damage_mult(self) -> float: return self._crit_damage_mult

    def tag_mult(self, stat: str, tag: str) -> float:
        return self._tag_mods.get((stat, tag), 0.0)

    def total_damage_for(self, base_damage: float, tags: frozenset[str]) -> float:
        dmg = base_damage * self._damage_mult
        for tag in tags:
            tag_bonus = self._tag_mods.get(("damage", tag), 0.0)
            if tag_bonus > 0.0:
                dmg *= (1.0 + tag_bonus)
        return dmg

    def total_speed_for(self, base_speed: float) -> float:
        return base_speed * self._move_speed_mult

    def total_attack_speed_for(self, base_speed: float) -> float:
        return base_speed * self._attack_speed_mult

    def apply_passive_modifier(self, stat: str, value: float, is_percent: bool, tag: str = "") -> None:
        """Apply a single passive modifier to cached values."""
        if tag:
            current = self._tag_mods.get((stat, tag), 0.0)
            self._tag_mods[(stat, tag)] = current + value
        elif stat == "damage" and is_percent:
            self._damage_mult *= (1.0 + value)
        elif stat == "max_health":
            self._max_health_bonus += value
        elif stat == "move_speed" and is_percent:
            self._move_speed_mult *= (1.0 + value)
        elif stat == "attack_speed" and is_percent:
            self._attack_speed_mult *= (1.0 + value)
        elif stat == "dodge_charges":
            self._dodge_charge_bonus += int(value)
        elif stat == "crit_chance":
            self._crit_chance += value

    def add_weapon_upgrade(self, stat: str, value: float) -> None:
        """Apply a run-time weapon upgrade (e.g. damage+10%, speed+5%)."""
        self.weapon_upgrades[stat] = self.weapon_upgrades.get(stat, 0.0) + value

    def get_weapon_upgrade(self, stat: str, default: float = 0.0) -> float:
        return self.weapon_upgrades.get(stat, default)

    def register_conditional(self, mod: dict) -> None:
        """Register a conditional modifier (e.g. Fury below 50% HP)."""
        self._conditional_mods.append(mod)

    def update_conditionals(self, current_hp: float, max_hp: float) -> None:
        """Evaluate conditional modifiers each frame. Called from scene."""
        for mod in self._conditional_mods:
            condition = mod.get("condition", "")
            if condition == "hp_below_50":
                should_be_active = current_hp <= max_hp * 0.5
                is_active = mod.get("_active", False)
                value = mod.get("value", 0.0)
                if should_be_active and not is_active:
                    # Apply Fury.
                    self._damage_mult *= (1.0 + value)
                    mod["_active"] = True
                    self._fury_active = True
                elif not should_be_active and is_active:
                    # Remove Fury.
                    self._damage_mult /= (1.0 + value)
                    mod["_active"] = False
                    self._fury_active = False
