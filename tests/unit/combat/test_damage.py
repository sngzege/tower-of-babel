"""Tests for the damage pipeline (Phase 4)."""

from __future__ import annotations

from gameplay.combat.damage import DamageInstance, DamagePipeline


class _DummyTarget:
    """Minimal DamageTarget implementation for tests."""

    def __init__(self, health: float = 100.0, invulnerable: bool = False) -> None:
        self._health = health
        self._max_health = health
        self._invulnerable = invulnerable

    @property
    def health(self) -> float:
        return self._health

    @health.setter
    def health(self, value: float) -> None:
        self._health = value

    @property
    def max_health(self) -> float:
        return self._max_health

    @property
    def invulnerable(self) -> bool:
        return self._invulnerable


def test_zero_damage_is_noop() -> None:
    pipe = DamagePipeline()
    target = _DummyTarget(health=100.0)
    result = pipe.apply(DamageInstance(value=0.0), target)
    assert result.dealt == 0.0
    assert not result.killed
    assert target.health == 100.0


def test_damage_reduces_health() -> None:
    pipe = DamagePipeline()
    target = _DummyTarget(health=100.0)
    result = pipe.apply(DamageInstance(value=25.0), target)
    assert result.dealt == 25.0
    assert target.health == 75.0
    assert not result.killed
    assert result.overkill == 0.0


def test_damage_can_kill() -> None:
    pipe = DamagePipeline()
    target = _DummyTarget(health=30.0)
    result = pipe.apply(DamageInstance(value=30.0), target)
    assert result.dealt == 30.0
    assert target.health == 0.0
    assert result.killed


def test_overkill_is_tracked() -> None:
    pipe = DamagePipeline()
    target = _DummyTarget(health=10.0)
    result = pipe.apply(DamageInstance(value=25.0), target)
    assert result.dealt == 10.0
    assert result.killed
    assert result.overkill == 15.0
    assert target.health == 0.0


def test_invulnerable_target_takes_no_damage() -> None:
    pipe = DamagePipeline()
    target = _DummyTarget(health=100.0, invulnerable=True)
    result = pipe.apply(DamageInstance(value=50.0), target)
    assert result.dealt == 0.0
    assert result.invulnerable
    assert not result.killed
    assert target.health == 100.0


def test_negative_damage_is_treated_as_zero() -> None:
    pipe = DamagePipeline()
    target = _DummyTarget(health=100.0)
    result = pipe.apply(DamageInstance(value=-10.0), target)
    assert result.dealt == 0.0
    assert target.health == 100.0


def test_damage_types_are_carried_through() -> None:
    pipe = DamagePipeline()
    target = _DummyTarget()
    dmg = DamageInstance(
        value=15.0,
        types=frozenset({"physical", "slashing"}),
        knockback=(10.0, 0.0),
        status_tags=frozenset({"bleed"}),
    )
    result = pipe.apply(dmg, target)
    assert result.dealt == 15.0
    assert target.health == 85.0


def test_apply_multi_stops_at_death() -> None:
    pipe = DamagePipeline()
    target = _DummyTarget(health=15.0)
    results = pipe.apply_multi(
        [
            DamageInstance(value=25.0),  # kills (15 dealt, 10 overkill)
            DamageInstance(value=15.0),  # should be skipped
        ],
        target,
    )
    assert len(results) == 1  # first kills, remaining skipped
    assert results[0].dealt == 15.0
    assert results[0].killed
    assert target.health == 0.0


def test_apply_multi_without_death_applies_all() -> None:
    pipe = DamagePipeline()
    target = _DummyTarget(health=100.0)
    results = pipe.apply_multi(
        [DamageInstance(value=10.0), DamageInstance(value=20.0)],
        target,
    )
    assert len(results) == 2
    assert results[0].dealt == 10.0
    assert results[1].dealt == 20.0
    assert target.health == 70.0
