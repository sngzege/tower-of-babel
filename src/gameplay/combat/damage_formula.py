"""Centralized damage formula for Tower of Babel.

One authoritative calculation path for all damage in the game.

FORMULA
-------
    attack_power = base_character_attack
                 + weapon_attack_bonus
                 + permanent_modifiers (future)
                 + run_modifiers     (boons, passives)

    base_damage = attack_power * coefficient

    final_damage = base_damage
                 * global_damage_multiplier
                 * product(1.0 + tag_multiplier) over matching tags
                 * conditional_damage_multiplier (active conditions only)
                 + flat_damage_bonus

    If critical_hit (crit_chance > roll):
        final_damage *= crit_damage_multiplier

The formula is designed so future systems (enemy resistances, armor,
difficulty scaling) can be added as additional multipliers without
rewriting the core path.
"""

from __future__ import annotations

import math
from typing import Protocol


class DamageBuildProvider(Protocol):
    """Interface for BuildState stats that the formula reads.

    This keeps DamageFormula decoupled from the full BuildState class.
    """

    @property
    def damage_mult(self) -> float: ...

    @property
    def crit_chance(self) -> float: ...

    @property
    def crit_damage_mult(self) -> float: ...

    def tag_mult(self, stat: str, tag: str) -> float: ...

    def total_damage_for(self, base_damage: float, tags: frozenset[str]) -> float: ...


class DamageFormula:
    """Stateless damage formula — call compute() to get the final value.

    Every caller (basic attack, ability, future weapon mod) routes through
    this single path.  No hardcoded damage numbers outside data files.
    """

    @staticmethod
    def basic_attack(
        attack_power: float,
        tags: frozenset[str],
        build: DamageBuildProvider | None = None,
        *,
        force_crit: bool = False,
        rng: float = 0.0,
    ) -> float:
        """Compute final damage for a basic / weapon attack.

        Parameters
        ----------
        attack_power : float
            The weapon-modified attack damage (base_attack * weapon.damage_mult).
        tags : frozenset[str]
            Attack type tags (e.g. 'physical', 'melee', 'sweep').
        build : DamageBuildProvider or None
            BuildState (or mock) providing multipliers.
        force_crit : bool
            Force a critical hit (for testing).
        rng : float
            Random 0..1 value; crit occurs if rng < build.crit_chance.

        Returns
        -------
        float
            Final damage after all multipliers.
        """
        return DamageFormula._compute(
            coefficient=1.0,
            attack_power=attack_power,
            tags=tags,
            build=build,
            force_crit=force_crit,
            rng=rng,
        )

    @staticmethod
    def ability_damage(
        coefficient: float,
        attack_power: float,
        tags: frozenset[str],
        build: DamageBuildProvider | None = None,
        *,
        force_crit: bool = False,
        rng: float = 0.0,
    ) -> float:
        """Compute final damage for an ability.

        Parameters
        ----------
        coefficient : float
            The ability's damage coefficient (scales with attack_power).
        attack_power : float
            The player's current attack power (from weapon + build).
        tags : frozenset[str]
            Ability/attack tags for tag-specific multipliers.
        build : DamageBuildProvider or None
            BuildState with global and tag multipliers.
        force_crit : bool
            Force critical hit (testing).
        rng : float
            Random value for crit check.

        Returns
        -------
        float
            Final damage after all multipliers.
        """
        if coefficient <= 0.0:
            return 0.0
        return DamageFormula._compute(
            coefficient=coefficient,
            attack_power=attack_power,
            tags=tags,
            build=build,
            force_crit=force_crit,
            rng=rng,
        )

    @staticmethod
    def _compute(
        coefficient: float,
        attack_power: float,
        tags: frozenset[str],
        build: DamageBuildProvider | None,
        force_crit: bool,
        rng: float,
    ) -> float:
        """Core formula computation."""
        # Step 1: base damage from attack_power * coefficient.
        base_damage = attack_power * coefficient

        # Step 2: apply BuildState multipliers.
        if build is not None:
            modified = build.total_damage_for(base_damage, tags)
        else:
            modified = base_damage

        # Step 3: critical hit.
        crit_chance = build.crit_chance if build is not None else 0.0
        is_crit = force_crit or (crit_chance > 0.0 and rng < crit_chance)
        if is_crit:
            crit_mult = build.crit_damage_mult if build is not None else 1.5
            modified *= crit_mult

        # Step 4: round to 1 decimal for cleaner display.
        return math.floor(modified * 10.0) / 10.0

    @staticmethod
    def multi_hit(
        coefficient: float,
        attack_power: float,
        tags: frozenset[str],
        hits: int,
        build: DamageBuildProvider | None = None,
        *,
        force_crit: bool = False,
        rng: float = 0.0,
    ) -> float:
        """Total damage for a multi-hit ability (each hit crits independently)."""
        per_hit = DamageFormula.ability_damage(
            coefficient / hits,  # distribute coefficient across hits
            attack_power,
            tags,
            build,
            force_crit=force_crit,
            rng=rng,
        )
        return per_hit * hits
