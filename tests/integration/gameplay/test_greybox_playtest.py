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
from world.stage_manager import StageManager

DT = 1.0 / 60.0
VIEWPORT = (320, 180)


class RecordingRenderer:
    """Renderer-protocol test double (framework-free)."""

    def __init__(self) -> None:
        self.rects: list[tuple[tuple[int, int, int, int], tuple[int, int, int]]] = []
        self.texts: list[str] = []

    @property
    def size(self) -> tuple[int, int]:
        return VIEWPORT

    def draw_rect(
        self, rect: tuple[int, int, int, int], color: tuple[int, int, int]
    ) -> None:
        self.rects.append((rect, color))

    def draw_text(self, text: str, x: int, y: int, color: tuple[int, int, int], font_size: int = 12) -> None:  # noqa: E501
        self.texts.append(text)

    def clear(self, color: tuple[int, int, int]) -> None:
        pass

    def present(self) -> None:
        pass

    def tick(self, fps: int) -> float:
        return 1.0 / 60.0

    def close(self) -> None:
        pass


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
    # Should at least have floor, all solids, player, and HUD elements.
    min_expected = 1 + len(scene.room.solids) + 2  # floor + walls + player (body + inner)
    assert len(renderer.rects) >= min_expected
    # Should have text output (HP, weapon, ability labels).
    assert len(renderer.texts) >= 5


def test_controller_translates_actions_into_intents() -> None:
    controller = PlayerController()
    intent = controller.build_intent(
        ActionFrame(pressed=frozenset({Action.DODGE}), move_x=1.0, move_y=1.0)
    )
    assert intent.dodge_pressed
    assert intent.wish_x == pytest.approx(2**-0.5)
    assert intent.wish_y == pytest.approx(2**-0.5)


def _build_full_stage_scene(seed: int = 42) -> tuple[PlaytestScene, StageManager]:
    """Build a full stage-enabled scene like main.py does."""
    from core.content_registry import ContentRegistry
    from core.data_loader import load_category
    from world.stage import StageConfig
    from world.stage_generator import generate_stage

    registry = ContentRegistry()
    for cat in ("player", "world", "enemies", "combat", "classes", "abilities", "passives", "weapons", "boons"):  # noqa: E501
        registry.register_all(load_category(cat))
    stage_config = StageConfig.from_document(registry.get("world", "first_stage"))
    stage_data = generate_stage(stage_config, registry, seed=seed)
    manager = StageManager(stage_data)
    start_room = manager.start()
    stats = PlayerStats.from_document(registry.get("player", "player_base"))
    spawn_x, spawn_y = start_room.player_spawn
    player = Player(stats=stats, x=spawn_x, y=spawn_y)
    camera = Camera(VIEWPORT, zoom=2.0, follow_stiffness=8.0, bounds=start_room.bounds)
    scene = PlaytestScene(
        player=player, room=start_room,
        world=start_room.build_collision_world(),
        camera=camera, registry=registry,
        stage_manager=manager,
    )
    scene.enter()
    return scene, manager


def test_full_vertical_slice_build_and_run() -> None:
    """End-to-end: start → combat → weapon choice → boon → boss → victory."""
    scene, manager = _build_full_stage_scene(seed=42)
    frame = ActionFrame()

    # Phase 1: Start room → walk to next room.
    assert scene.room.kind == "start"
    assert scene._run.build.weapon_id == "warrior_sword"
    assert len(scene._run.build.ability_ids) == 4

    # Walk to the first combat room.
    door = max(scene.room.doors, key=lambda d: d.box.x)
    scene.player.body.teleport(door.box.x + 8.0, door.box.y + door.box.height / 2.0)
    scene.update(frame, DT)
    assert scene.room.kind == "combat"

    # Phase 2: Clear first combat room and select a boon.
    boons = 0
    for step in range(8):
        if scene._encounter.active:
            for enemy, _ai in scene.enemies:
                enemy.health = 0.0
                scene._encounter.on_enemy_died()
            scene.update(frame, DT)
            if scene._reward_pending:
                scene.update(ActionFrame(aim_x=1.0), DT)
                boons += 1
                break
        scene.update(frame, DT)
    assert boons == 1, "should have collected one boon"
    assert len(scene._run.build.boon_ids) == 1

    # Phase 3: Walk to boss floor by following rightmost doors.
    MAX_STEPS = 64
    for step in range(MAX_STEPS):
        if scene.stage_completed or manager.stage_complete:
            break
        if scene.room.kind == "boss" and scene._boss is not None:
            if scene._boss.alive:
                scene._boss.health = 0.0
                scene._encounter.on_enemy_died()
            # Walk through exit door.
            exit_door = max(scene.room.doors, key=lambda d: d.box.x)
            scene.player.body.teleport(
                exit_door.box.x + 8.0, exit_door.box.y + exit_door.box.height / 2.0
            )
            scene.update(frame, DT)
            continue
        # Walk through rightmost door.
        door = max(scene.room.doors, key=lambda d: d.box.x)
        scene.player.body.teleport(
            door.box.x + 8.0, door.box.y + door.box.height / 2.0
        )
        scene.update(frame, DT)

    # Phase 3: Verify stage complete.
    assert scene.stage_completed, (
        f"stage not completed. floor: {manager.floor_index + 1}/{len(manager.stage_data.floors)}"
        f", boss: {scene._boss is not None}"
        f", ended: {scene._run.ended}"
        f", phase: {scene._run.state.phase.value}"
    )
    assert scene._run.ended
    assert scene._run.state.phase.value == "victory"

    # Phase 4: Build persisted throughout.
    assert scene._run.build.weapon_id == "warrior_sword"
    assert len(scene._run.build.boon_ids) > 0
    assert len(scene._run.build.ability_ids) == 4

    # Phase 5: Restart command resets build.
    scene._restart_run()
    assert scene._run.build.weapon_id == "warrior_sword"  # class loadout
    assert len(scene._run.build.boon_ids) == 0
    assert scene.player.health > 0

    # Phase 6: Death → restart resets build.
    scene.player.health = 0.0
    scene.player.die()
    scene.update(frame, DT)
    assert scene._run.ended
    assert scene._run.state.phase.value == "death"
    scene.update(ActionFrame(pressed=frozenset({Action.PRIMARY_ATTACK})), DT)
    assert scene._run.build.weapon_id == "warrior_sword"
    assert len(scene._run.build.boon_ids) == 0
    assert scene.player.health > 0