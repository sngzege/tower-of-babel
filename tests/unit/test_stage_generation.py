"""Tests for Phase 7/8 stage generation: data-driven, seeded, multi-floor + boss floor.

Verifies:
  - Stage data loads through the registry into a StageConfig.
  - Stage config parsing rejects malformed documents.
  - generate_stage produces config.floor_count + 1 floors (boss floor appended).
  - Floor room counts respect the stage's configured bounds (boss floor exempt).
  - Determinism: same seed → same logical stage; different seeds vary.
  - Every room of every floor is reachable.
  - Every floor's exit room has a floor-exit door (boss floor included).
  - Encounters are populated from data and reference real enemy ids.
  - StageManager drives room→room, floor→floor, and stage completion.
  - All room templates in the pools are structurally valid.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.content_registry import ContentRegistry
from core.data_loader import load_category
from physics.collision import AABB
from world.floor_assembler import (
    _KIND_TO_TEMPLATES,
    FLOOR_EXIT_TARGET,
    FloorData,
)
from world.room import Door, Room
from world.stage import StageConfig, StageConfigError, StageData
from world.stage_generator import floor_seed_for, generate_stage
from world.stage_manager import StageManager

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_ENEMY_HALF = 12.0


@pytest.fixture(scope="module")
def registry() -> ContentRegistry:
    """Shared registry loaded once per module (world + enemies)."""
    reg = ContentRegistry()
    for entry in load_category("world", data_dir=_DATA_DIR):
        reg.register(entry)
    for entry in load_category("enemies", data_dir=_DATA_DIR):
        reg.register(entry)
    return reg


@pytest.fixture(scope="module")
def stage_config(registry: ContentRegistry) -> StageConfig:
    return StageConfig.from_document(registry.get("world", "first_stage"))


def _reachable_room_ids(floor: FloorData) -> set[str]:
    """BFS from the start room over room→room connections."""
    seen = {floor.start_room_id}
    stack = [floor.start_room_id]
    while stack:
        current = stack.pop()
        for _door, target in floor.connections.get(current, []):
            if target not in seen:
                seen.add(target)
                stack.append(target)
    return seen


def _floor_signature(floor: FloorData) -> tuple:
    """A comparable snapshot of a floor's logical structure."""
    return (
        tuple(sorted(floor.rooms)),
        tuple(sorted(floor.templates.items())),
        tuple(sorted(floor.encounters.items())),
        tuple(
            sorted(
                (room_id, tuple(sorted(door.target_room for door in room.doors)))
                for room_id, room in floor.rooms.items()
            )
        ),
    )


def _stage_signature(stage: StageData) -> tuple:
    return tuple(_floor_signature(floor) for floor in stage.floors)


def _exit_door(floor: FloorData) -> Door:
    exit_room = floor.rooms[floor.exit_room_id]
    return next(
        door for door in exit_room.doors if door.target_room == FLOOR_EXIT_TARGET
    )


# -- Stage data loading and config parsing --


def test_first_stage_document_loads(
    registry: ContentRegistry, stage_config: StageConfig
) -> None:
    """first_stage.yaml parses into the expected configuration."""
    assert stage_config.stage_id == "first_stage"
    assert stage_config.floor_count == 3
    assert stage_config.min_rooms == 4
    assert stage_config.max_rooms == 7
    assert stage_config.branch_chance == 0.0
    assert stage_config.index == 0


def test_config_rejects_missing_floors() -> None:
    with pytest.raises(StageConfigError):
        StageConfig.from_document({"id": "bad", "name": "Bad", "index": 0})


def test_config_rejects_bad_room_bounds() -> None:
    document = {
        "id": "bad",
        "name": "Bad",
        "index": 0,
        "floors": {"count": 2, "min_rooms": 8, "max_rooms": 5},
    }
    with pytest.raises(StageConfigError):
        StageConfig.from_document(document)


def test_config_rejects_zero_floors() -> None:
    document = {
        "id": "bad",
        "name": "Bad",
        "index": 0,
        "floors": {"count": 0, "min_rooms": 4, "max_rooms": 6},
    }
    with pytest.raises(StageConfigError):
        StageConfig.from_document(document)


def test_config_rejects_bad_branch_chance() -> None:
    document = {
        "id": "bad",
        "name": "Bad",
        "index": 0,
        "floors": {"count": 1, "min_rooms": 3, "max_rooms": 4, "branch_chance": 1.5},
    }
    with pytest.raises(StageConfigError):
        StageConfig.from_document(document)


# -- Parameterized multi-floor generation --


def test_generate_stage_creates_configured_floor_count(
    registry: ContentRegistry, stage_config: StageConfig
) -> None:
    """generate_stage adds one boss floor, so total = config.floor_count + 1."""
    stage = generate_stage(stage_config, registry, seed=42)
    assert stage.floor_count == stage_config.floor_count + 1 == 4


def test_floor_room_counts_within_stage_bounds(
    registry: ContentRegistry, stage_config: StageConfig
) -> None:
    """Each normal floor's room count is driven by the stage's min/max rooms.
    The boss floor is a single room and is exempt from this check."""
    for seed in range(1, 11):
        stage = generate_stage(stage_config, registry, seed=seed)
        # All floors except the last (boss floor).
        for floor in stage.floors[:-1]:
            assert stage_config.min_rooms <= len(floor.rooms) <= stage_config.max_rooms


def test_room_bounds_are_parameterized_by_config(
    registry: ContentRegistry,
) -> None:
    """A different stage config produces different room-count bounds."""
    config = StageConfig(
        stage_id="custom",
        name="Custom",
        index=1,
        floor_count=2,
        min_rooms=3,
        max_rooms=3,
    )
    stage = generate_stage(config, registry, seed=7)
    assert stage.floor_count == 3  # 2 normal + 1 boss
    for floor in stage.floors[:-1]:
        assert len(floor.rooms) == 3
    assert len(stage.floors[-1].rooms) == 1  # boss floor


def test_floor_seed_derivation_is_stable() -> None:
    assert floor_seed_for(42, "first_stage", 0) == floor_seed_for(42, "first_stage", 0)
    assert floor_seed_for(42, "first_stage", 0) != floor_seed_for(42, "first_stage", 1)


# -- Determinism --


def test_same_seed_produces_same_stage(
    registry: ContentRegistry, stage_config: StageConfig
) -> None:
    stage_a = generate_stage(stage_config, registry, seed=123)
    stage_b = generate_stage(stage_config, registry, seed=123)
    assert _stage_signature(stage_a) == _stage_signature(stage_b)


def test_different_seeds_vary_stage(
    registry: ContentRegistry, stage_config: StageConfig
) -> None:
    """Across seeds, template selection / room counts must vary."""
    signatures = set()
    for seed in range(1, 11):
        stage = generate_stage(stage_config, registry, seed=seed)
        signatures.add(_stage_signature(stage))
    assert len(signatures) >= 2


def test_template_pools_actually_used(
    registry: ContentRegistry, stage_config: StageConfig
) -> None:
    """Across seeds, multiple templates per kind must appear (variety)."""
    combat_templates: set[str] = set()
    start_templates: set[str] = set()
    boss_templates: set[str] = set()
    for seed in range(1, 21):
        stage = generate_stage(stage_config, registry, seed=seed)
        for floor_idx, floor in enumerate(stage.floors):
            for room_id, template in floor.templates.items():
                kind = floor.rooms[room_id].kind
                if kind == "combat":
                    combat_templates.add(template)
                elif kind == "start":
                    start_templates.add(template)
                elif kind == "boss":
                    boss_templates.add(template)
    assert len(combat_templates) >= 2
    assert len(start_templates) >= 2
    assert "greybox_boss_arena" in boss_templates


# -- Reachability and floor exits --


def test_every_room_reachable_from_start(
    registry: ContentRegistry, stage_config: StageConfig
) -> None:
    """All floors must be fully connected."""
    for seed in range(1, 11):
        stage = generate_stage(stage_config, registry, seed=seed)
        for floor in stage.floors:
            reachable = _reachable_room_ids(floor)
            assert reachable == set(floor.rooms)


def test_every_floor_exit_reachable_and_has_exit_door(
    registry: ContentRegistry, stage_config: StageConfig
) -> None:
    for seed in range(1, 11):
        stage = generate_stage(stage_config, registry, seed=seed)
        for floor in stage.floors:
            assert floor.exit_room_id in _reachable_room_ids(floor)
            exit_room = floor.rooms[floor.exit_room_id]
            assert any(
                door.target_room == FLOOR_EXIT_TARGET for door in exit_room.doors
            )


# -- Encounter population --


def test_encounters_populated_from_data(
    registry: ContentRegistry, stage_config: StageConfig
) -> None:
    """Combat rooms get enemies; start/exit rooms get none; boss room has first_boss."""
    for seed in range(1, 6):
        stage = generate_stage(stage_config, registry, seed=seed)
        for floor in stage.floors:
            for room_id, room in floor.rooms.items():
                encounter = floor.encounters[room_id]
                if room.kind == "combat":
                    assert encounter, f"{room_id} (combat) has no encounter"
                elif room.kind == "boss":
                    # Boss floor should have a boss encounter.
                    for enemy_id, count in encounter:
                        assert enemy_id == "first_boss"
                        assert count == 1
                else:
                    assert encounter == (), f"{room_id} ({room.kind}) populated"
                for enemy_id, count in encounter:
                    assert registry.has("enemies", enemy_id)
                    assert count >= 1


def test_encounter_density_matches_template(
    registry: ContentRegistry,
) -> None:
    """The pillar template spawns 3 dummies; hall/basic spawn 2 (data-driven)."""
    config = StageConfig(
        stage_id="custom",
        name="Custom",
        index=1,
        floor_count=1,
        min_rooms=5,
        max_rooms=5,
    )
    stage = generate_stage(config, registry, seed=42)
    # First floor (index 0) is the normal floor.
    floor = stage.floors[0]
    for room_id, template in floor.templates.items():
        total = sum(count for _enemy, count in floor.encounters[room_id])
        if template == "greybox_combat_pillars":
            assert total == 3
        elif template in ("greybox_room", "greybox_combat_hall"):
            assert total == 2


# -- StageManager traversal --


def test_stage_manager_walks_all_floors_to_completion(
    registry: ContentRegistry, stage_config: StageConfig
) -> None:
    """All floors (incl. boss) advance to stage complete."""
    stage = generate_stage(stage_config, registry, seed=42)
    manager = StageManager(stage)
    transitions: list[tuple[str, float, float]] = []
    completions: list[bool] = []
    manager.on_transition(lambda room, x, y: transitions.append((room.room_id, x, y)))
    manager.on_stage_complete(lambda: completions.append(True))

    _ = manager.start()  # initialize the first floor
    # 3 normal floors + 1 boss floor = 4 floors total.
    for i in range(stage.floor_count - 1):
        manager.transition(_exit_door(stage.floors[i]))
        assert manager.floor_index == i + 1
        assert manager.current_room_id == stage.floors[i + 1].start_room_id
        assert not manager.stage_complete

    # Boss floor exit → stage complete.
    _last = stage.floor_count - 1
    manager.transition(_exit_door(stage.floors[_last]))
    assert manager.stage_complete
    assert completions == [True]

    # Further exit attempts are inert.
    manager.transition(_exit_door(stage.floors[_last]))
    assert completions == [True]


def test_stage_manager_room_transition_within_floor(
    registry: ContentRegistry, stage_config: StageConfig
) -> None:
    """Room→room doors move inside the floor and fire the callback."""
    stage = generate_stage(stage_config, registry, seed=42)
    manager = StageManager(stage)
    seen: list[str] = []
    manager.on_transition(lambda room, _x, _y: seen.append(room.room_id))
    manager.start()

    floor = stage.floors[0]
    start_room = floor.rooms[floor.start_room_id]
    door = start_room.doors[0]
    manager.transition(door)
    assert manager.floor_index == 0
    assert manager.current_room_id == door.target_room
    assert seen == [door.target_room]


def test_stage_manager_check_transition_detects_overlap(
    registry: ContentRegistry, stage_config: StageConfig
) -> None:
    stage = generate_stage(stage_config, registry, seed=42)
    manager = StageManager(stage)
    start_room = manager.start()
    door = start_room.doors[0]
    inside = AABB(door.box.x, door.box.y, 4.0, 4.0)
    assert manager.check_transition(inside) is door
    far_away = AABB(400.0, 100.0, 4.0, 4.0)
    assert manager.check_transition(far_away) is None


# -- Template structural validity --


def _all_pool_templates() -> list[str]:
    return sorted({t for pool in _KIND_TO_TEMPLATES.values() for t in pool})


def test_all_pool_templates_parse_and_are_valid(
    registry: ContentRegistry,
) -> None:
    """Every template in the pools: valid doc, spawn in bounds, has doors."""
    for template_id in _all_pool_templates():
        room = Room.from_document(registry.get("world", template_id))
        sx, sy = room.player_spawn
        assert 0 <= sx <= room.width, template_id
        assert 0 <= sy <= room.height, template_id
        assert room.doors, f"{template_id} has no doors"


def test_template_enemy_spawns_valid(registry: ContentRegistry) -> None:
    """Enemy spawn points are in bounds and don't collide with solids."""
    for template_id in _all_pool_templates():
        room = Room.from_document(registry.get("world", template_id))
        for x, y in room.enemy_spawns:
            assert 0 <= x <= room.width, f"{template_id} spawn x out of bounds"
            assert 0 <= y <= room.height, f"{template_id} spawn y out of bounds"
            body = AABB(
                x - _ENEMY_HALF, y - _ENEMY_HALF, _ENEMY_HALF * 2, _ENEMY_HALF * 2
            )
            for solid in room.solids:
                assert not body.intersects(solid), (
                    f"{template_id} enemy spawn ({x}, {y}) overlaps a solid"
                )


def test_template_door_slots_match_kind_convention(
    registry: ContentRegistry,
) -> None:
    """Start templates need a right slot; others need left+right."""
    for template_id in _all_pool_templates():
        room = Room.from_document(registry.get("world", template_id))
        has_left = any(door.box.x < 50.0 for door in room.doors)
        has_right = any(door.box.x > 900.0 for door in room.doors)
        if room.kind == "start":
            assert has_right, f"{template_id} (start) lacks a right door slot"
        else:
            assert has_left, f"{template_id} ({room.kind}) lacks a left slot"
            assert has_right, f"{template_id} ({room.kind}) lacks a right slot"


def test_entry_spawns_are_not_inside_solids(registry: ContentRegistry) -> None:
    """The conventional entry spawn points must be walkable."""
    conventional_spawns = [(80.0, 304.0), (928.0, 304.0)]
    for template_id in _all_pool_templates():
        room = Room.from_document(registry.get("world", template_id))
        for x, y in conventional_spawns:
            body = AABB(x - 10.0, y - 10.0, 20.0, 20.0)
            for solid in room.solids:
                assert not body.intersects(solid), (
                    f"{template_id} entry spawn ({x}, {y}) overlaps a solid"
                )
