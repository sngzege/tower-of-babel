"""Tests for engine entity/component/system (hybrid model, Phase 2)."""

from __future__ import annotations

import pytest

from engine.component import Component
from engine.entity import Entity
from engine.system import System


class Health(Component):
    def __init__(self, amount: int) -> None:
        self.amount = amount


class Position(Component):
    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.x = x
        self.y = y


class _Gravity(System):
    required = (Position,)

    def update(self, entity: Entity, dt: float) -> None:
        entity.get(Position).y += 10.0 * dt


def test_add_get_has_component() -> None:
    entity = Entity("hero")
    entity.add(Health(10))
    assert entity.has(Health)
    assert entity.get(Health).amount == 10
    assert not entity.has(Position)


def test_duplicate_component_raises() -> None:
    entity = Entity()
    entity.add(Health(10))
    with pytest.raises(ValueError):
        entity.add(Health(20))


def test_missing_component_raises() -> None:
    with pytest.raises(KeyError):
        Entity().get(Health)


def test_remove_component() -> None:
    entity = Entity()
    entity.add(Health(10))
    entity.remove(Health)
    assert not entity.has(Health)


def test_system_processes_only_matching_entities() -> None:
    with_pos, without_pos = Entity("a"), Entity("b")
    with_pos.add(Position())
    without_pos.add(Health(5))
    processed = _Gravity().process([with_pos, without_pos], dt=1.0)
    assert processed == 1
    assert with_pos.get(Position).y == pytest.approx(10.0)


def test_unique_uids() -> None:
    assert Entity().uid != Entity().uid
