"""Shared fixtures for player unit tests (Phase 3)."""

from __future__ import annotations

import pytest

from gameplay.player.player import Player
from gameplay.player.player_stats import PlayerStats
from physics.collision import CollisionWorld


@pytest.fixture()
def stats() -> PlayerStats:
    """Tuning identical to data/player/stats.yaml (greybox base profile)."""
    return PlayerStats(
        move_speed=100.0,
        acceleration=1000.0,
        friction=1300.0,
        roll_distance=76.0,
        roll_duration=0.34,
        dodge_invulnerability=0.2,
        dodge_cooldown=1.5,
        dodge_max_charges=2,
        max_health=100.0,
        max_mana=50.0,
        attack_speed=1.0,
        body_width=14.0,
        body_height=12.0,
        hitbox_width=18.0,
        hitbox_height=16.0,
        hitbox_offset_x=0.0,
        hitbox_offset_y=0.0,
        hurtbox_width=12.0,
        hurtbox_height=12.0,
        hurtbox_offset_x=0.0,
        hurtbox_offset_y=0.0,
    )


@pytest.fixture()
def world() -> CollisionWorld:
    return CollisionWorld()


@pytest.fixture()
def player(stats: PlayerStats) -> Player:
    return Player(stats=stats, x=0.0, y=0.0)
