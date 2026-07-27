"""Tests for aim controller: movement/aim independence, priority, facing (Phase 3.5).

Tests 1-6, 10-12 run on AimController directly (no camera needed; mock
callbacks). Tests 7-9 (mouse screen->world + camera offset/zoom) also test
camera.screen_to_world independently in test_camera.py.
"""

from __future__ import annotations

import pytest

from gameplay.player.aim_controller import AimController
from gameplay.player.player_controller import PlayerIntent
from input.input_manager import ActionFrame
from physics.movement import Direction8, clamp_magnitude


def _mock_camera(sx: float, sy: float) -> tuple[float, float]:
    return (sx - 320.0, sy - 180.0)


def _controller(callback=_mock_camera) -> AimController:
    return AimController(screen_to_world=callback)


@pytest.fixture()
def aim() -> AimController:
    return _controller()


# -- Movement and aim independence (tests 1-5) --


def test_movement_and_aim_independent(aim: AimController) -> None:
    """W only moves; arrow key only aims."""
    frame = ActionFrame(move_y=-1.0)
    result = aim.resolve(frame, 0.0, 0.0)
    assert result.source == "held"  # neither aim nor mouse changed; retains default
    assert result.direction == (0.0, -1.0)


def test_w_produces_northward_movement() -> None:
    """W -> negative Y movement (north = screen up)."""
    wish_x, wish_y = clamp_magnitude(0.0, -1.0)
    intent = PlayerIntent(wish_x=wish_x, wish_y=wish_y)
    assert intent.wish_y == pytest.approx(-1.0)


def test_down_arrow_produces_southward_aim(aim: AimController) -> None:
    frame = ActionFrame(aim_y=1.0)
    result = aim.resolve(frame, 0.0, 0.0)
    assert result.source == "keyboard"
    assert Direction8.from_vector(*result.direction) is Direction8.DOWN


def test_w_and_down_arrow_independent() -> None:
    """W (move north) + down arrow (aim south) -> independent channels."""
    aim = _controller()
    frame = ActionFrame(move_y=-1.0, aim_y=1.0)
    result = aim.resolve(frame, 0.0, 0.0)
    assert result.source == "keyboard"
    assert result.direction[1] > 0.0  # aiming south
    wish_x, wish_y = clamp_magnitude(0.0, -1.0)
    assert wish_y < 0.0  # moving north


def test_diagonal_movement_does_not_alter_aim(aim: AimController) -> None:
    """Set aim left, then diagonal movement -> aim stays left."""
    aim.resolve(ActionFrame(aim_x=-1.0), 0.0, 0.0)
    frame = ActionFrame(move_x=0.707, move_y=0.707)
    result = aim.resolve(frame, 0.0, 0.0)
    assert result.source == "keyboard"
    assert result.direction[0] < 0.0


# -- Persistence (test 6) --


def test_aim_persists_without_new_input(aim: AimController) -> None:
    aim.resolve(ActionFrame(aim_x=1.0), 0.0, 0.0)
    for _ in range(5):
        result = aim.resolve(ActionFrame(), 0.0, 0.0)
        assert result.source == "keyboard"
        assert result.direction[0] > 0.0


# -- Mouse screen->world (test 7) --


def test_mouse_aim_screen_to_world() -> None:
    """Screen (400, 280) with mock camera(origin=0) -> world (80, 100)."""
    aim = _controller()
    frame = ActionFrame(pointer=(400.0, 280.0), pointer_moved=True)
    result = aim.resolve(frame, 0.0, 0.0)
    assert result.source == "mouse"
    assert result.direction[0] > 0.0
    assert result.direction[1] > 0.0
