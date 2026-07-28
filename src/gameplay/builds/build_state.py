"""Build state: authoritative representation of the player's current run build.

The BuildState is the single source of truth for what the player has equipped
and what effects are active. It is owned by the run lifecycle, not by Player.

BuildState is reset on run start and discarded on run end.

Components (PROVISIONAL — expands with future phases):
  - weapon: determines attack behavior
  - abilities: active skills (Q/E/R)
  - passives: permanent modifiers (from class/items)
  - boons: temporary run buffs (from rewards)

Effects are NOT applied directly to Player fields here.
Instead, BuildState exposes computed modifier values that Player/combat
systems consume through a well-defined interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# -- Tag system --

# Recognised tags (provisional — extends as needed).
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


# -- Modifier types --


@dataclass(frozen=True)
class StatModifier:
    """A single numeric modifier to a player stat.

    ``stat`` is the stat name (e.g. 'damage', 'move_speed', 'max_health').
    ``value`` is the amount (flat or percent).
    ``is_percent`` — True: multiply base by (1 + value). False: add value.
    ``source`` — id of the build component that created this modifier.
    ``tags`` — tag filter: only applies if the affected system matches these tags.
    """
    stat: str
    value: float
    is_percent: bool = False
    source: str = ""
    tags: frozenset[str] = frozenset()


@dataclass(frozen=True)
class BuildComponent:
    """Base metadata for any piece of a build."""
    id: str
    name: str
    description: str = ""
    tags: frozenset[str] = frozenset()


# -- Fully immutable build state --


@dataclass(frozen=False)
class BuildState:
    """Authoritative run build. Mutable during run, discarded on death.

    Call ``compute_effects()`` to derive aggregated modifiers after changes.
    """

    weapon_id: str = "unarmed"
    ability_ids: list[str] = field(default_factory=list)
    passive_ids: list[str] = field(default_factory=list)
    boon_ids: list[str] = field(default_factory=list)

    # Cached modifiers — recompute after any change.
    _damage_mult: float = 1.0
    _move_speed_mult: float = 1.0
    _attack_speed_mult: float = 1.0
    _max_health_bonus: float = 0.0
    _dodge_charge_bonus: int = 0
    _crit_chance: float = 0.0
    _crit_damage_mult: float = 1.5  # base crit multiplier

    # Tag-specific modifiers: {(stat, tag): multiplier}
    _tag_mods: dict[tuple[str, str], float] = field(default_factory=dict)

    def reset(self) -> None:
        """Clear all build components (new run)."""
        self.weapon_id = "unarmed"
        self.ability_ids.clear()
        self.passive_ids.clear()
        self.boon_ids.clear()
        self._damage_mult = 1.0
        self._move_speed_mult = 1.0
        self._attack_speed_mult = 1.0
        self._max_health_bonus = 0.0
        self._dodge_charge_bonus = 0
        self._crit_chance = 0.0
        self._crit_damage_mult = 1.5
        self._tag_mods.clear()

    @property
    def damage_mult(self) -> float:
        return self._damage_mult

    @property
    def move_speed_mult(self) -> float:
        return self._move_speed_mult

    @property
    def attack_speed_mult(self) -> float:
        return self._attack_speed_mult

    @property
    def max_health_bonus(self) -> float:
        return self._max_health_bonus

    @property
    def dodge_charge_bonus(self) -> int:
        return self._dodge_charge_bonus

    @property
    def crit_chance(self) -> float:
        return self._crit_chance

    @property
    def crit_damage_mult(self) -> float:
        return self._crit_damage_mult

    def tag_mult(self, stat: str, tag: str) -> float:
        """Return the cumulative multiplier for a (stat, tag) pair."""
        return self._tag_mods.get((stat, tag), 0.0)

    def total_damage_for(self, base_damage: float, tags: frozenset[str]) -> float:
        """Compute final damage applying all relevant modifiers.

        Applies:
          1. Global damage multiplier
          2. Per-tag damage multipliers
        """
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
