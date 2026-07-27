"""Tests for rendering.camera: follow, zoom, bounds, pixel snapping (Phase 3)."""

from __future__ import annotations

import pytest

from physics.collision import AABB
from rendering.camera import Camera

VIEWPORT = (320, 180)


def test_center_on_snaps_instantly() -> None:
    camera = Camera(VIEWPORT)
    camera.center_on(100.0, 50.0)
    assert (camera.x, camera.y) == (100.0, 50.0)


def test_follow_converges_on_target() -> None:
    camera = Camera(VIEWPORT, follow_stiffness=8.0)
    for _ in range(600):
        camera.follow(300.0, 200.0, 1.0 / 60.0)
    assert camera.x == pytest.approx(300.0, abs=0.5)
    assert camera.y == pytest.approx(200.0, abs=0.5)


def test_follow_moves_smoothly_not_instantly() -> None:
    camera = Camera(VIEWPORT, follow_stiffness=8.0)
    camera.follow(100.0, 0.0, 1.0 / 60.0)
    assert 0.0 < camera.x < 100.0  # eased, not snapped


def test_zoom_must_be_positive() -> None:
    with pytest.raises(ValueError):
        Camera(VIEWPORT, zoom=0.0)


def test_world_to_screen_applies_zoom_and_rounds() -> None:
    camera = Camera(VIEWPORT, zoom=2.0)
    camera.center_on(0.0, 0.0)
    assert camera.world_to_screen(0.0, 0.0) == (160, 90)  # viewport center
    assert camera.world_to_screen(10.0, -5.0) == (180, 80)
    assert camera.world_to_screen(0.26, 0.0) == (161, 90)  # pixel-perfect snap


def test_screen_rect_rounds_both_corners() -> None:
    camera = Camera(VIEWPORT, zoom=2.0)
    camera.center_on(0.0, 0.0)
    rect = camera.screen_rect(AABB(-5.0, -5.0, 10.0, 10.0))
    assert rect == (150, 80, 20, 20)


def test_shake_offset_shifts_output() -> None:
    camera = Camera(VIEWPORT)
    camera.center_on(0.0, 0.0)
    camera.shake_offset = (5.0, -3.0)
    assert camera.world_to_screen(0.0, 0.0) == (165, 87)


def test_bounds_clamp_keeps_view_inside_room() -> None:
    bounds = AABB(0.0, 0.0, 1000.0, 1000.0)
    camera = Camera(VIEWPORT, zoom=1.0, bounds=bounds)
    for _ in range(600):
        camera.follow(2000.0, -2000.0, 1.0 / 60.0)
    assert camera.x == 1000.0 - 160.0  # half viewport at zoom 1
    assert camera.y == 0.0 + 90.0


def test_bounds_smaller_than_view_center_the_camera() -> None:
    bounds = AABB(0.0, 0.0, 200.0, 100.0)  # smaller than the 320x180 view
    camera = Camera(VIEWPORT, zoom=1.0, bounds=bounds)
    camera.center_on(10.0, 10.0)
    assert (camera.x, camera.y) == (100.0, 50.0)  # locked to bounds center


def test_set_bounds_none_unlocks_camera() -> None:
    camera = Camera(VIEWPORT, bounds=AABB(0.0, 0.0, 100.0, 100.0))
    camera.set_bounds(None)
    camera.center_on(500.0, 500.0)
    assert (camera.x, camera.y) == (500.0, 500.0)
