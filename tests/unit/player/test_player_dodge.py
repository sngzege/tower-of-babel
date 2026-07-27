"""Tests for the player dodge/roll: i-frames, velocity, control (Phase 3)."""

from __future__ import annotations

import pytest

from core.events import EventBus
from gameplay.player.player import EVENT_DODGE, EVENT_STATE_CHANGED, Player
from gameplay.player.player_controller import PlayerIntent
from gameplay.player.player_state import PlayerState
from gameplay.player.player_stats import PlayerStats
from physics.collision import CollisionWorld
from physics.movement import Direction8

DT = 1.0 / 60.0
IDLE_INTENT = PlayerIntent()
DODGE_RIGHT = PlayerIntent(wish_x=1.0, dodge_pressed=True)


def _roll(
    player: Player, world: CollisionWorld, intent: PlayerIntent, frames: int
) -> None:
    for _ in range(frames):
        player.update(intent, world, DT)


def test_dodge_starts_on_press_and_moves_at_roll_speed(
    player: Player, world: CollisionWorld, stats: PlayerStats
) -> None:
    player.update(DODGE_RIGHT, world, DT)
    assert player.state is PlayerState.DODGE
    assert player.body.vx == pytest.approx(stats.roll_speed)
    assert player.body.vy == pytest.approx(0.0)


def test_roll_covers_configured_distance(
    player: Player, world: CollisionWorld, stats: PlayerStats
) -> None:
    start_x = player.body.x
    frames = 0
    player.update(DODGE_RIGHT, world, DT)
    frames += 1
    while player.state is PlayerState.DODGE and frames < 600:
        player.update(IDLE_INTENT, world, DT)
        frames += 1
    traveled = player.body.x - start_x
    # Integrates whole frames: distance plus at most one extra frame of roll.
    assert stats.roll_distance <= traveled
    assert traveled <= stats.roll_distance + stats.roll_speed * DT


def test_iframes_active_only_inside_configured_window(
    player: Player, world: CollisionWorld, stats: PlayerStats
) -> None:
    player.update(DODGE_RIGHT, world, DT)
    assert player.invulnerable
    assert not player.hurtbox.vulnerable  # hurtbox mirrors i-frames

    # Still inside the window: invulnerable.
    while player._iframe_remaining > 0.0:  # noqa: SLF001
        player.update(IDLE_INTENT, world, DT)
    # Window consumed but the roll continues: vulnerable again.
    assert player.state is PlayerState.DODGE
    assert not player.invulnerable
    assert player.hurtbox.vulnerable


def test_roll_returns_to_idle_without_input(
    player: Player, world: CollisionWorld
) -> None:
    _roll(player, world, DODGE_RIGHT, 1)
    _roll(player, world, IDLE_INTENT, 60)
    assert player.state is PlayerState.IDLE


def test_roll_returns_to_move_with_held_input(
    player: Player, world: CollisionWorld
) -> None:
    _roll(player, world, DODGE_RIGHT, 1)
    _roll(player, world, PlayerIntent(wish_x=1.0), 60)
    assert player.state is PlayerState.MOVE


def test_dodge_during_roll_is_ignored(
    player: Player, world: CollisionWorld
) -> None:
    player.update(DODGE_RIGHT, world, DT)
    for _ in range(3):
        player.update(PlayerIntent(wish_x=1.0), world, DT)
    # A second press (now steering up) must not restart or redirect the roll.
    player.update(PlayerIntent(wish_y=-1.0, dodge_pressed=True), world, DT)
    assert player.body.vy == pytest.approx(0.0)  # still rolling straight right
    assert player.body.vx > 0.0


def test_dodge_uses_facing_without_move_input(
    player: Player, world: CollisionWorld, stats: PlayerStats
) -> None:
    player.facing = Direction8.LEFT
    player.update(PlayerIntent(dodge_pressed=True), world, DT)
    assert player.state is PlayerState.DODGE
    assert player.body.vx == pytest.approx(-stats.roll_speed)


def test_diagonal_roll_is_unit_speed(
    player: Player, world: CollisionWorld, stats: PlayerStats
) -> None:
    player.update(PlayerIntent(wish_x=0.5, wish_y=0.5, dodge_pressed=True), world, DT)
    assert player.body.speed == pytest.approx(stats.roll_speed)


def test_movement_states_follow_input(player: Player, world: CollisionWorld) -> None:
    assert player.state is PlayerState.IDLE
    player.update(PlayerIntent(wish_x=1.0), world, DT)
    assert player.state is PlayerState.MOVE
    assert player.facing is Direction8.RIGHT
    _roll(player, world, IDLE_INTENT, 120)  # let friction stop the body
    assert player.state is PlayerState.IDLE


def test_animation_hook_exposes_state_and_facing(player: Player) -> None:
    player.facing = Direction8.UP_RIGHT
    pose = player.animation_pose
    assert pose.state is PlayerState.IDLE
    assert pose.facing is Direction8.UP_RIGHT
    assert pose.clip_name == "idle_up_right"


def test_events_are_published(stats: PlayerStats, world: CollisionWorld) -> None:
    bus = EventBus()
    seen: list[tuple[str, dict]] = []
    bus.subscribe(EVENT_DODGE, lambda e: seen.append((e.name, e.payload)))
    bus.subscribe(EVENT_STATE_CHANGED, lambda e: seen.append((e.name, e.payload)))
    player = Player(stats=stats, x=0.0, y=0.0, events=bus)
    player.update(DODGE_RIGHT, world, DT)
    names = [name for name, _ in seen]
    assert names == [EVENT_STATE_CHANGED, EVENT_DODGE]
    assert seen[0][1] == {"old": "idle", "new": "dodge"}
