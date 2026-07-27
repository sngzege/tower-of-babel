"""Tests for the status effect framework (Phase 4)."""

from __future__ import annotations

import pytest

from gameplay.combat.status_effects import StatusEffectData, StatusEffectManager


def _effect(**overrides) -> StatusEffectData:
    params = dict(
        id="test_effect",
        name="Test Effect",
        duration=3.0,
        tick_interval=0.0,
        tags=frozenset(),
        modifiers={},
        max_stacks=1,
    )
    params.update(overrides)
    return StatusEffectData(**params)


def test_empty_manager() -> None:
    mgr = StatusEffectManager()
    assert mgr.active == []


def test_apply_adds_effect() -> None:
    mgr = StatusEffectManager()
    mgr.apply(_effect())
    assert mgr.has("test_effect")
    assert mgr.active


def test_has_tag() -> None:
    mgr = StatusEffectManager()
    mgr.apply(_effect(tags=frozenset({"fire", "damage_over_time"})))
    assert mgr.has_tag("fire")
    assert mgr.has_tag("damage_over_time")
    assert not mgr.has_tag("cold")


def test_expires_after_duration() -> None:
    mgr = StatusEffectManager()
    mgr.apply(_effect(duration=1.0))
    assert mgr.has("test_effect")
    expired = mgr.update(0.6)
    assert expired == []
    assert mgr.has("test_effect")
    expired = mgr.update(0.5)
    assert expired == ["test_effect"]
    assert not mgr.has("test_effect")


def test_zero_duration_does_nothing() -> None:
    mgr = StatusEffectManager()
    mgr.apply(_effect(duration=0.0))
    assert not mgr.has("test_effect")


def test_negative_duration_does_nothing() -> None:
    mgr = StatusEffectManager()
    mgr.apply(_effect(duration=-1.0))
    assert not mgr.has("test_effect")


def test_remove_effect() -> None:
    mgr = StatusEffectManager()
    mgr.apply(_effect())
    assert mgr.remove("test_effect")
    assert not mgr.has("test_effect")
    assert not mgr.remove("test_effect")


def test_stack_refreshes_duration() -> None:
    mgr = StatusEffectManager()
    mgr.apply(_effect(duration=3.0, max_stacks=3))
    mgr.update(1.5)  # remaining = 1.5
    mgr.apply(_effect(duration=3.0, max_stacks=3))
    assert mgr.get("test_effect") is not None
    assert mgr.get("test_effect").stacks == 2
    assert mgr.get("test_effect").remaining == 3.0  # refreshed


def test_stacks_capped() -> None:
    mgr = StatusEffectManager()
    eff = _effect(duration=3.0, max_stacks=2)
    mgr.apply(eff)
    mgr.apply(eff)
    mgr.apply(eff)  # should cap at 2
    assert mgr.get("test_effect").stacks == 2


def test_get_modifier_aggregation() -> None:
    mgr = StatusEffectManager()
    mgr.apply(_effect(id="slow", modifiers={"move_speed_mult": -0.3}))
    mgr.apply(_effect(id="freeze", modifiers={"move_speed_mult": -0.5}))
    assert mgr.get_modifier("move_speed_mult") == pytest.approx(-0.8)
    assert mgr.get_modifier("nonexistent") == 0.0


def test_clear_removes_all() -> None:
    mgr = StatusEffectManager()
    mgr.apply(_effect(id="a"))
    mgr.apply(_effect(id="b"))
    mgr.clear()
    assert mgr.active == []


def test_tick_timer_does_not_tick_without_interval() -> None:
    mgr = StatusEffectManager()
    mgr.apply(_effect(duration=5.0, tick_interval=0.0))
    # Tick timer should stay at 0 since tick_interval=0 means no ticks
    inst = mgr.get("test_effect")
    assert inst is not None
    assert inst.tick_timer == 0.0


def test_applying_same_effect_returns_true_only_first_time() -> None:
    mgr = StatusEffectManager()
    eff = _effect()
    assert mgr.apply(eff)  # first time: True (was applied)
    assert mgr.apply(eff)  # refreshed: True (stacks incremented)
