"""Tests for the attack executor lifecycle (Phase 4)."""

from __future__ import annotations

import pytest

from gameplay.combat.attack import AttackData, AttackExecutor, AttackPhase

DT = 1.0 / 60.0


def _attack_data(**overrides) -> AttackData:
    """Create attack data with sensible defaults."""
    params = dict(
        id="test_attack",
        windup=0.05,
        active=0.15,
        recovery=0.1,
        cooldown=0.3,
        damage=25.0,
        damage_types=frozenset({"physical"}),
        hitbox_spread=16.0,
        hitbox_reach=36.0,
    )
    params.update(overrides)
    return AttackData(**params)


def test_starts_idle() -> None:
    exe = AttackExecutor(_attack_data())
    assert exe.state.phase is AttackPhase.IDLE
    assert exe.can_trigger()


def test_trigger_starts_windup() -> None:
    exe = AttackExecutor(_attack_data())
    assert exe.trigger()
    assert exe.state.phase is AttackPhase.WINDUP
    assert not exe.can_trigger()


def test_cannot_trigger_while_active() -> None:
    exe = AttackExecutor(_attack_data(windup=0.0))
    exe.trigger()
    exe.update(0.01)
    assert exe.state.phase is AttackPhase.ACTIVE
    assert not exe.trigger()


def test_windup_to_active() -> None:
    exe = AttackExecutor(_attack_data(windup=0.1))
    exe.trigger()
    exe.update(0.05)
    assert exe.state.phase is AttackPhase.WINDUP
    exe.update(0.05)
    assert exe.state.phase is AttackPhase.ACTIVE


def test_hitbox_active_only_in_active_phase() -> None:
    exe = AttackExecutor(_attack_data(windup=0.05, active=0.1))
    exe.trigger()
    assert not exe.hitbox_active()
    exe.update(0.05)  # now active
    assert exe.hitbox_active()
    exe.update(0.05)
    assert exe.hitbox_active()
    exe.update(0.06)  # total active elapsed = 0.11 > 0.1
    assert not exe.hitbox_active()


def test_active_to_recovery_to_cooldown_to_idle() -> None:
    exe = AttackExecutor(_attack_data(
        windup=0.0, active=0.1, recovery=0.05, cooldown=0.2
    ))
    exe.trigger()
    exe.update(0.01)
    assert exe.state.phase is AttackPhase.ACTIVE

    exe.update(0.1)  # move to recovery
    assert exe.state.phase is AttackPhase.RECOVERY

    exe.update(0.05)  # move to cooldown
    assert exe.state.phase is AttackPhase.COOLDOWN

    exe.update(0.2)  # cooldown done
    assert exe.state.phase is AttackPhase.IDLE


def test_no_cooldown_skips_phase() -> None:
    exe = AttackExecutor(_attack_data(
        windup=0.0, active=0.1, recovery=0.05, cooldown=0.0
    ))
    exe.trigger()
    exe.update(0.01)  # windup -> active (windup=0, immediate)
    assert exe.state.phase is AttackPhase.ACTIVE
    exe.update(0.1)  # active done
    assert exe.state.phase is AttackPhase.RECOVERY
    exe.update(0.05)  # recovery done
    assert exe.state.phase is AttackPhase.IDLE


def test_cancel_resets_to_idle() -> None:
    exe = AttackExecutor(_attack_data())
    exe.trigger()
    assert exe.state.phase is AttackPhase.WINDUP
    exe.cancel()
    assert exe.state.phase is AttackPhase.IDLE
    assert exe.can_trigger()


def test_hitbox_for_returns_none_when_not_active() -> None:
    exe = AttackExecutor(_attack_data())
    assert exe.hitbox_for(100.0, 100.0) is None


def test_hitbox_for_returns_aabb_when_active() -> None:
    exe = AttackExecutor(_attack_data(
        windup=0.0, active=0.1, hitbox_spread=14.0, hitbox_reach=30.0
    ))
    exe.trigger()
    exe.update(0.01)
    aabb = exe.hitbox_for(100.0, 100.0, facing_x=1.0, facing_y=0.0)
    assert aabb is not None
    # Facing RIGHT: AABB should be ~30 wide (reach) x ~14 tall (spread).
    assert aabb.width == pytest.approx(30.0, abs=0.001)
    assert aabb.height == pytest.approx(14.0, abs=0.001)

    # Facing DOWN: AABB should be ~14 wide x ~30 tall.
    aabb2 = exe.hitbox_for(100.0, 100.0, facing_x=0.0, facing_y=1.0)
    assert aabb2 is not None
    assert aabb2.width == pytest.approx(14.0, abs=0.001)
    assert aabb2.height == pytest.approx(30.0, abs=0.001)

    # Facing diagonal UP-RIGHT: AABB smoothly interpolates.
    aabb3 = exe.hitbox_for(100.0, 100.0, facing_x=0.707, facing_y=-0.707)
    assert aabb3 is not None
    assert aabb3.width > 14.0  # between the two extremes
    assert aabb3.height > 14.0


def test_full_attack_cycle_returns_to_idle() -> None:
    exe = AttackExecutor(_attack_data(
        windup=0.05, active=0.1, recovery=0.05, cooldown=0.2
    ))
    exe.trigger()
    total = 0.0
    while exe.state.phase is not AttackPhase.IDLE:
        exe.update(DT)
        total += DT
        if total > 1.0:  # safety
            break
    assert exe.state.phase is AttackPhase.IDLE
    assert exe.can_trigger()
