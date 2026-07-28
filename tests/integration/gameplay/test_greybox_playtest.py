"""Integration: the greybox slice, built from real data files.

Drives PlaytestScene with scripted ActionFrames (no pygame) and verifies the
playtest targets: spawn, movement, wall collision, dodge, camera follow, and
rendering calls. Legacy single-room mode; stage mode is tested separately.
"""

from __future__ import annotations

import pytest

from core.content_registry import ContentRegistry
from core.data_loader import load_category
from gameplay.player.player import Player
from gameplay.player.player_controller import PlayerController
from gameplay.player.player_state import PlayerState
from gameplay.player.player_stats import PlayerStats
from gameplay.playtest_scene import PlaytestScene
from input.input_manager import Action, ActionFrame
from rendering.camera import Camera
from world.room import Room

DT = 1.0 / 60.0
VIEWPORT = (320, 180)


class RecordingRenderer:
    """Renderer-protocol test double (framework-free)."""

    def __init__(self) -> None:
        self.rects: list[tuple[tuple[int, int, int, int], tuple[int, int, int]]] = []

    @property
    def size(self) -> tuple[int, int]:
        return VIEWPORT

    def draw_rect(
        self, rect: tuple[int, int, int, int], color: tuple[int, int, int]
    ) -> None:
        self.rects.append((rect, color))


def _build_scene() -> PlaytestScene:
    registry = ContentRegistry()
    registry.register_all(load_category("player"))
    registry.register_all(load_category("world"))
    stats = PlayerStats.from_document(registry.get("player", "player_base"))
    room = Room.from_document(registry.get("world", "greybox_arena"))
    world = room.build_collision_world()
    spawn_x, spawn_y = room.player_spawn
    player = Player(stats=stats, x=spawn_x, y=spawn_y)
    camera = Camera(VIEWPORT, zoom=2.0, follow_stiffness=8.0, bounds=room.bounds)
    scene = PlaytestScene(
        player=player,
        room=room,
        world=world,
        camera=camera,
        enemies=[],
    )
    scene.enter()
    return scene


def _run(scene: PlaytestScene, frame: ActionFrame, frames: int) -> None:
    for _ in range(frames):
        scene.update(frame, DT)


def test_player_moves_and_camera_follows() -> None:
    scene = _build_scene()
    start_x = scene.player.body.x
    _run(scene, ActionFrame(move_x=1.0), 60)
    assert scene.player.body.x > start_x + 30.0
    assert scene.player.state is PlayerState.MOVE
    _run(scene, ActionFrame(move_x=1.0), 60)
    assert scene.camera.x == pytest.approx(scene.player.body.x, abs=15.0)


def test_player_cannot_cross_walls() -> None:
    scene = _build_scene()
    room = scene.room
    scene.player.body.teleport(room.width - 100.0, 100.0)
    _run(scene, ActionFrame(move_x=1.0), 600)
    right_wall = next(
        s for s in room.solids if s.x >= 900.0 and s.y < scene.player.body.y + 200.0
    )
    assert scene.player.body.box.right <= right_wall.left + 1e-6


def test_dodge_grants_iframes_and_rolls() -> None:
    scene = _build_scene()
    start_x = scene.player.body.x
    dodge = ActionFrame(pressed=frozenset({Action.DODGE}), move_x=1.0)
    scene.update(dodge, DT)
    assert scene.player.state is PlayerState.DODGE
    assert scene.player.invulnerable
    _run(scene, ActionFrame(), 60)
    assert scene.player.body.x > start_x + 40.0


def test_scene_renders_floor_walls_player_and_marker() -> None:
    scene = _build_scene()
    renderer = RecordingRenderer()
    scene.render(renderer)
    # 1 floor + N solids + 1 player + 1 marker + ability HUD (4 slots × 2 rects each).
    expected = 1 + len(scene.room.solids) + 2 + 8
    assert len(renderer.rects) == expected


def test_controller_translates_actions_into_intents() -> None:
    controller = PlayerController()
    intent = controller.build_intent(
        ActionFrame(pressed=frozenset({Action.DODGE}), move_x=1.0, move_y=1.0)
    )
    assert intent.dodge_pressed
    assert intent.wish_x == pytest.approx(2**-0.5)
    assert intent.wish_y == pytest.approx(2**-0.5)
