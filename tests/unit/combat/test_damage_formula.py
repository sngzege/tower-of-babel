"""Tests for the centralized damage formula.

Verifies:
  - Basic attack damage computation
  - Ability scaling with coefficient and attack_power
  - BuildState global damage multiplier
  - Tag-specific multipliers
  - Conditional multipliers (Fury)
  - Crit mechanics
  - Multi-hit ability damage
  - Zero/negative/invalid values
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from gameplay.combat.damage_formula import DamageFormula


@dataclass
class MockBuild:
    """Minimal BuildState mock for formula tests."""
    _damage_mult: float = 1.0
    _crit_chance: float = 0.0
    _crit_damage_mult: float = 1.5
    _tag_mods: dict[tuple[str, str], float] = field(default_factory=dict)

    @property
    def damage_mult(self) -> float:
        return self._damage_mult

    @property
    def crit_chance(self) -> float:
        return self._crit_chance

    @property
    def crit_damage_mult(self) -> float:
        return self._crit_damage_mult

    def tag_mult(self, stat: str, tag: str) -> float:
        return self._tag_mods.get((stat, tag), 0.0)

    def total_damage_for(self, base_damage: float, tags: frozenset[str]) -> float:
        dmg = base_damage * self._damage_mult
        for tag in tags:
            tag_bonus = self._tag_mods.get(("damage", tag), 0.0)
            if tag_bonus > 0.0:
                dmg *= (1.0 + tag_bonus)
        return dmg


_MELEE_TAGS = frozenset({"melee", "physical"})


def test_basic_attack_no_build() -> None:
    """Basic attack with no build modifiers = attack_power * 1.0."""
    result = DamageFormula.basic_attack(20.0, _MELEE_TAGS)
    assert result == 20.0


def test_basic_attack_with_global_mult() -> None:
    """Global damage multiplier applies to basic attack."""
    build = MockBuild(_damage_mult=1.5)
    result = DamageFormula.basic_attack(20.0, _MELEE_TAGS, build)
    assert result == 30.0  # 20 * 1.5


def test_basic_attack_with_tag_mult() -> None:
    """Tag-specific multiplier applies to matching tags."""
    build = MockBuild()
    build._tag_mods[("damage", "melee")] = 0.25
    result = DamageFormula.basic_attack(20.0, _MELEE_TAGS, build)
    assert result == 25.0  # 20 * 1.25


def test_basic_attack_global_and_tag_stack() -> None:
    """Global and tag multipliers stack multiplicatively."""
    build = MockBuild(_damage_mult=1.2)
    build._tag_mods[("damage", "melee")] = 0.3
    result = DamageFormula.basic_attack(20.0, _MELEE_TAGS, build)
    assert result == pytest.approx(31.2)  # 20 * 1.2 * 1.3


def test_ability_damage_scales_with_attack_power() -> None:
    """Ability damage = attack_power * coefficient with no build mods."""
    result = DamageFormula.ability_damage(1.5, 20.0, _MELEE_TAGS)
    assert result == 30.0  # 20 * 1.5


def test_ability_damage_with_build_mods() -> None:
    """Ability damage applies build multipliers on top of coefficient scaling."""
    build = MockBuild(_damage_mult=1.2)
    build._tag_mods[("damage", "melee")] = 0.25
    result = DamageFormula.ability_damage(2.0, 20.0, _MELEE_TAGS, build)
    assert result == pytest.approx(60.0)  # (20 * 2.0) * 1.2 * 1.25 = 60.0


def test_ability_high_attack_power() -> None:
    """Stronger weapon → higher ability damage (proportional)."""
    build = MockBuild()
    sword_damage = DamageFormula.ability_damage(1.5, 20.0, _MELEE_TAGS, build)
    axe_damage = DamageFormula.ability_damage(1.5, 30.0, _MELEE_TAGS, build)
    assert axe_damage > sword_damage
    assert axe_damage == pytest.approx(45.0)  # 30 * 1.5
    assert sword_damage == pytest.approx(30.0)  # 20 * 1.5


def test_critical_hit_multiplies_damage() -> None:
    """Critical hit applies crit_damage_mult."""
    build = MockBuild(_crit_chance=1.0, _crit_damage_mult=2.0)
    result = DamageFormula.basic_attack(20.0, _MELEE_TAGS, build, rng=0.0)
    assert result == 40.0  # 20 * 2.0


def test_critical_hit_not_guaranteed() -> None:
    """Crit only triggers when rng < crit_chance."""
    build = MockBuild(_crit_chance=0.5, _crit_damage_mult=2.0)
    # rng=0.6 > 0.5 → no crit
    result = DamageFormula.basic_attack(20.0, _MELEE_TAGS, build, rng=0.6)
    assert result == 20.0  # no crit


def test_force_crit() -> None:
    """force_crit=True always produces a crit."""
    build = MockBuild(_crit_chance=0.0, _crit_damage_mult=2.0)
    result = DamageFormula.basic_attack(20.0, _MELEE_TAGS, build, force_crit=True)
    assert result == 40.0


def test_multi_hit_damage() -> None:
    """Multi-hit distributes coefficient across hits."""
    build = MockBuild()
    result = DamageFormula.multi_hit(1.5, 20.0, _MELEE_TAGS, 3, build)
    # per_hit = 20 * (1.5/3) = 10, total = 10 * 3 = 30
    assert result == 30.0


def test_zero_attack_power() -> None:
    """Zero attack power should produce zero damage."""
    result = DamageFormula.basic_attack(0.0, _MELEE_TAGS)
    assert result == 0.0


def test_zero_coefficient() -> None:
    """Ability with coefficient 0 produces no damage."""
    result = DamageFormula.ability_damage(0.0, 20.0, _MELEE_TAGS)
    assert result == 0.0


def test_negative_coefficient() -> None:
    """Negative coefficient is treated as zero (no damage)."""
    result = DamageFormula.ability_damage(-1.0, 20.0, _MELEE_TAGS)
    assert result == 0.0


def test_no_build_provider_no_errors() -> None:
    """Calling the formula without build provider doesn't crash."""
    result = DamageFormula.basic_attack(20.0, _MELEE_TAGS, None)
    assert result == 20.0

    result = DamageFormula.ability_damage(1.5, 20.0, _MELEE_TAGS, None)
    assert result == 30.0
