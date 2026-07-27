"""Integration: full Stage 1 traversal through the real PlaytestScene.

Builds the stage exactly like main.py does (registry → StageConfig →
generate_stage → StageManager → PlaytestScene) and simulates a player
walking through every room of every floor by teleporting into door boxes,
verifying: room→room transitions, floor→floor transitions, encounter
population per room, and the final stage completion.
"""

from __future__ import annotations

from core.content_registry import ContentRegistry
from core.data_loader import load_category
from gameplay.player.player import Player
from gameplay.player.player_stats import PlayerStats
from gameplay.playtest_scene import PlaytestScene
from input.input_manager import ActionFrame
from rendering.camera import Camera
from world.floor_assembler import FLOOR_EXIT_TARGET
from world.stage import StageConfig
from world.stage_generator import generate_stage
from world.stage_manager import StageManager

DT = 1.0 / 60.0
VIEWPORT = (320, 180)
MAX_STEPS = 64  # safety bound for the walkthrough loop


def _build_stage_scene(seed: int = 42) -> tuple[PlaytestScene, StageManager]:
    registry = ContentRegistry()
    for category in ("player", "world", "enemies"):
        registry.register_all(load_category(category))
    stage_config = StageConfig.from_document(registry.get("world", "first_stage"))
    stage_data = generate_stage(stage_config, registry, seed=seed)
    manager = StageManager(stage_data)
    start_room = manager.start()
    stats = PlayerStats.from_document(registry.get("player", "player_base"))
    spawn_x, spawn_y = start_room.player_spawn
    player = Player(stats=stats, x=spawn_x, y=spawn_y)
    camera = Camera(VIEWPORT, zoom=2.0, follow_stiffness=8.0, bounds=start_room.bounds)
    scene = PlaytestScene(
        player=player,
        room=start_room,
        world=start_room.build_collision_world(),
        camera=camera,
        registry=registry,
        stage_manager=manager,
    )
    scene.enter()
    return scene, manager


def _walk_through_rightmost_door(scene: PlaytestScene) -> None:
    """Teleport the player into the current room's deepest (right) door."""
    door = max(scene.room.doors, key=lambda d: d.box.x)
    scene.player.body.teleport(door.box.x + 8.0, door.box.y + door.box.height / 2.0)
    scene.update(ActionFrame(), DT)


def _walk_to_completion(seed: int) -> tuple[list[str], StageManager, PlaytestScene]:
    """Walk a stage to completion; return (visited templates, manager, scene)."""
    scene, manager = _build_stage_scene(seed=seed)
    templates = [manager.current_floor.templates[scene.room.room_id]]
    for _ in range(MAX_STEPS):
        if manager.stage_complete:
            break
        _walk_through_rightmost_door(scene)
        template = manager.current_floor.templates[scene.room.room_id]
        if template != templates[-1]:
            templates.append(template)
    return templates, manager, scene


def test_player_spawns_on_floor_1_start_room() -> None:
    scene, manager = _build_stage_scene()
    assert manager.floor_index == 0
    assert scene.room.room_id == manager.current_floor.start_room_id
    assert not manager.stage_complete
    assert not scene.stage_completed


def test_full_stage_walkthrough_reaches_stage_exit() -> None:
    """Walk start → floor exits → final exit across all 3 floors."""
    scene, manager = _build_stage_scene(seed=42)
    visited_floors = {manager.floor_index}
    rooms_visited: list[str] = [scene.room.room_id]
    saw_enemies = False

    for _ in range(MAX_STEPS):
        if manager.stage_complete:
            break
        _walk_through_rightmost_door(scene)
        visited_floors.add(manager.floor_index)
        if scene.room.room_id != rooms_visited[-1]:
            rooms_visited.append(scene.room.room_id)
        if scene.enemies:
            saw_enemies = True

    assert manager.stage_complete, (
        f"stage not complete after walk; rooms visited: {rooms_visited}"
    )
    assert scene.stage_completed
    assert visited_floors == {0, 1, 2}
    # Every floor start room was entered via its floor's exit door.
    for floor_index in (1, 2):
        start_id = manager.stage_data.floors[floor_index].start_room_id
        assert start_id in rooms_visited
    assert saw_enemies, "no enemies encountered during the walkthrough"


def test_combat_rooms_spawn_enemies_on_entry() -> None:
    """Entering a combat room populates it from the encounter data."""
    scene, manager = _build_stage_scene(seed=42)
    # Walk into the first combat room (start room's right door).
    assert not scene.enemies  # start room has no encounter
    _walk_through_rightmost_door(scene)
    assert scene.room.kind == "combat"
    encounter = manager.current_floor.encounters[scene.room.room_id]
    expected = sum(count for _enemy, count in encounter)
    assert len(scene.enemies) == expected > 0
    for enemy, _ai in scene.enemies:
        assert enemy.alive


def test_enemy_spawn_positions_match_template_data() -> None:
    """Spawned enemies stand on the template's declared spawn points."""
    scene, manager = _build_stage_scene(seed=42)
    _walk_through_rightmost_door(scene)
    assert scene.room.enemy_spawns, "combat template should declare spawns"
    declared = set(scene.room.enemy_spawns)
    for enemy, _ai in scene.enemies:
        assert (enemy.body.x, enemy.body.y) in declared


def test_floor_exit_door_is_the_rightmost_in_exit_room() -> None:
    """The exit room's floor-exit door targets the sentinel, not a room."""
    _scene, manager = _build_stage_scene(seed=42)
    for floor in manager.stage_data.floors:
        exit_room = floor.rooms[floor.exit_room_id]
        rightmost = max(exit_room.doors, key=lambda d: d.box.x)
        assert rightmost.target_room == FLOOR_EXIT_TARGET


def test_stage_traversal_deterministic_per_seed() -> None:
    """Two scenes built from the same seed walk the same template sequence."""
    walk_a, manager_a, _s1 = _walk_to_completion(7)
    walk_b, manager_b, _s2 = _walk_to_completion(7)
    assert manager_a.stage_complete and manager_b.stage_complete
    assert walk_a == walk_b


def test_different_seeds_may_walk_different_template_sequences() -> None:
    """Sanity: seeds 1..6 produce at least two distinct walk sequences."""
    sequences = set()
    for seed in range(1, 7):
        templates, manager, _scene = _walk_to_completion(seed)
        assert manager.stage_complete
        sequences.add(tuple(templates))
    assert len(sequences) >= 2


def test_scene_stays_consistent_after_completion() -> None:
    """The scene keeps updating without errors after the stage is complete."""
    _templates, manager, scene = _walk_to_completion(42)
    assert manager.stage_complete
    scene.update(ActionFrame(), DT)
    assert scene.room.room_id == manager.current_room_id
    assert scene.player.body is not None
