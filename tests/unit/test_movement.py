"""Tests for physics.movement: integration math and KinematicBody (Phase 3)."""

from __future__ import annotations

import math

import pytest

from physics.collision import AABB, CollisionWorld, StaticCollider
from physics.movement import (
    Direction8,
    KinematicBody,
    approach,
    clamp_magnitude,
)


def test_approach_moves_both_ways_without_overshoot() -> None:
    assert approach(0.0, 10.0, 3.0) == 3.0
    assert approach(10.0, 0.0, 3.0) == 7.0
    assert approach(9.0, 10.0, 3.0) == 10.0  # clamps at target
    assert approach(-9.0, -10.0, 3.0) == -10.0


def test_clamp_magnitude_caps_diagonals_only() -> None:
    x, y = clamp_magnitude(1.0, 1.0)
    assert math.isclose(math.hypot(x, y), 1.0)
    assert clamp_magnitude(0.3, 0.0) == (0.3, 0.0)  # analog partial kept
    assert clamp_magnitude(2.0, 0.0) == (1.0, 0.0)
    assert clamp_magnitude(0.0, 0.0) == (0.0, 0.0)


def test_direction8_from_vector_octants() -> None:
    assert Direction8.from_vector(1.0, 0.0) is Direction8.RIGHT
    assert Direction8.from_vector(1.0, 1.0) is Direction8.DOWN_RIGHT
    assert Direction8.from_vector(0.1, 1.0) is Direction8.DOWN
    assert Direction8.from_vector(-1.0, 1.0) is Direction8.DOWN_LEFT
    assert Direction8.from_vector(-1.0, 0.0) is Direction8.LEFT
    assert Direction8.from_vector(-1.0, -1.0) is Direction8.UP_LEFT
    assert Direction8.from_vector(0.0, -1.0) is Direction8.UP
    assert Direction8.from_vector(1.0, -1.0) is Direction8.UP_RIGHT
    with pytest.raises(ValueError):
        Direction8.from_vector(0.0, 0.0)


def test_direction8_vectors_are_unit() -> None:
    for direction in Direction8:
        assert math.isclose(math.hypot(*direction.vector), 1.0)


def test_accelerate_reaches_max_speed() -> None:
    body = KinematicBody(x=0.0, y=0.0, width=10.0, height=10.0)
    for _ in range(120):
        body.accelerate(1.0, 0.0, 120.0, 1000.0, 1300.0, 1.0 / 60.0)
    assert body.vx == pytest.approx(120.0)
    assert body.speed == pytest.approx(120.0)


def test_accelerate_scales_with_input_magnitude() -> None:
    body = KinematicBody(x=0.0, y=0.0, width=10.0, height=10.0)
    for _ in range(120):
        body.accelerate(0.5, 0.0, 120.0, 1000.0, 1300.0, 1.0 / 60.0)
    assert body.vx == pytest.approx(60.0)  # analog half-tilt = half speed


def test_friction_stops_body_without_overshoot() -> None:
    body = KinematicBody(x=0.0, y=0.0, width=10.0, height=10.0, vx=50.0)
    for _ in range(120):
        body.accelerate(0.0, 0.0, 120.0, 1000.0, 1300.0, 1.0 / 60.0)
    assert body.vx == 0.0


def test_diagonal_speed_capped_at_max() -> None:
    body = KinematicBody(x=0.0, y=0.0, width=10.0, height=10.0)
    diag = math.sqrt(0.5)
    for _ in range(120):
        body.accelerate(diag, diag, 120.0, 1000.0, 1300.0, 1.0 / 60.0)
    assert body.speed == pytest.approx(120.0)


def test_integrate_moves_and_zeroes_velocity_on_contact() -> None:
    world = CollisionWorld([StaticCollider(AABB(30.0, -50.0, 10.0, 100.0))])
    body = KinematicBody(x=0.0, y=0.0, width=10.0, height=10.0, vx=600.0)
    result = body.integrate(world, 1.0 / 10.0)  # would move 60px without wall
    assert result.hit_x
    assert body.box.right == 30.0
    assert body.vx == 0.0


def test_integrate_teleport_clears_velocity() -> None:
    world = CollisionWorld()
    body = KinematicBody(x=0.0, y=0.0, width=10.0, height=10.0, vx=10.0)
    body.teleport(100.0, 50.0)
    assert (body.x, body.y, body.vx, body.vy) == (100.0, 50.0, 0.0, 0.0)
    body.set_velocity(12.0, 0.0)
    body.integrate(world, 0.5)
    assert body.x == pytest.approx(106.0)
