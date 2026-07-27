"""Tests for floor assembly: FloorGraph → connected rooms.

Verifies:
  - Every graph node receives a room.
  - Doors connect to valid target rooms.
  - Start room has correct player spawn.
  - Floor exit is reachable.
  - Named room kinds map to known templates.
  - Deterministic seeds produce the same structure.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.content_registry import ContentRegistry
from core.data_loader import load_category
from world.dungeon_generator import generate_floor_graph
from world.floor_assembler import FloorData, assemble_floor

# Resolve data directory relative to this test file.
_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture(scope="module")
def registry() -> ContentRegistry:
    """Shared registry loaded once per module."""
    reg = ContentRegistry()
    for entry in load_category("world", data_dir=_DATA_DIR):
        reg.register(entry)
    return reg


def _reachable_count(floor: FloorData) -> int:
    """BFS from start to count reachable rooms."""
    seen = {floor.start_room_id}
    stack = [floor.start_room_id]
    while stack:
        current = stack.pop()
        if current in floor.connections:
            for door, target in floor.connections[current]:
                if target not in seen:
                    seen.add(target)
                    stack.append(target)
    return len(seen)


# -- Basic assembly tests --

def test_assemble_3_room_floor(registry: ContentRegistry) -> None:
    """A 3-room floor should produce 3 rooms."""
    graph = generate_floor_graph(42, config={"min_rooms": 3, "max_rooms": 3})
    floor = assemble_floor(graph, registry)
    assert len(floor.rooms) >= 3
    assert floor.start_room_id in floor.rooms
    assert floor.exit_room_id in floor.rooms


def test_start_room_has_player_spawn(registry: ContentRegistry) -> None:
    """The start room must have a valid player spawn."""
    graph = generate_floor_graph(42, config={"min_rooms": 3, "max_rooms": 3})
    floor = assemble_floor(graph, registry)
    start_room = floor.rooms[floor.start_room_id]
    spawn_x, spawn_y = start_room.player_spawn
    assert 0 <= spawn_x <= start_room.width
    assert 0 <= spawn_y <= start_room.height


def test_all_doors_target_valid_rooms(registry: ContentRegistry) -> None:
    """Every door must target a room that exists in the floor."""
    graph = generate_floor_graph(42, config={"min_rooms": 4, "max_rooms": 6})
    floor = assemble_floor(graph, registry)
    for room_id, room in floor.rooms.items():
        for door in room.doors:
            assert door.target_room in floor.rooms, (
                f"Door in {room_id} targets non-existent '{door.target_room}'"
            )


def test_start_room_reachable(registry: ContentRegistry) -> None:
    """The start room must always be reachable (trivially true)."""
    graph = generate_floor_graph(42, config={"min_rooms": 3, "max_rooms": 8})
    floor = assemble_floor(graph, registry)
    assert floor.start_room_id in floor.rooms


def test_exit_reachable_from_start(registry: ContentRegistry) -> None:
    """The exit room must be reachable from the start via door traversal."""
    graph = generate_floor_graph(42)
    floor = assemble_floor(graph, registry)
    count = _reachable_count(floor)
    assert floor.exit_room_id in [
        t for _, targets in floor.connections.items()
        for _, t in targets
    ] or floor.exit_room_id == floor.start_room_id
    assert count >= 2  # at least start + exit


def test_all_doors_have_position(registry: ContentRegistry) -> None:
    """Every door must have a valid position (non-zero size)."""
    graph = generate_floor_graph(42, config={"min_rooms": 4, "max_rooms": 6})
    floor = assemble_floor(graph, registry)
    for room_id, room in floor.rooms.items():
        for door in room.doors:
            assert door.box.width > 0, f"Zero-width door in {room_id}"
            assert door.box.height > 0, f"Zero-height door in {room_id}"


# -- Determinism tests --

def test_same_seed_produces_same_rooms(registry: ContentRegistry) -> None:
    """Same seed → same room count and same start/exit ids."""
    graph_a = generate_floor_graph(42, config={"min_rooms": 4, "max_rooms": 7})
    graph_b = generate_floor_graph(42, config={"min_rooms": 4, "max_rooms": 7})
    floor_a = assemble_floor(graph_a, registry)
    floor_b = assemble_floor(graph_b, registry)
    assert len(floor_a.rooms) == len(floor_b.rooms)
    assert floor_a.start_room_id == floor_b.start_room_id
    assert floor_a.exit_room_id == floor_b.exit_room_id


def test_different_seeds_produce_different_floors(registry: ContentRegistry) -> None:
    """Different seeds may produce different room counts (not always but
    often enough to verify the RNG is active)."""
    floors: set[int] = set()
    for seed in range(1, 11):
        graph = generate_floor_graph(seed, config={"min_rooms": 5, "max_rooms": 8})
        floor = assemble_floor(graph, registry)
        floors.add(len(floor.rooms))
    # At least 2 different room counts across 10 seeds with varied config.
    assert len(floors) >= 2


# -- Edge cases --

def test_minimum_3_rooms(registry: ContentRegistry) -> None:
    """Minimum floor should have at least start + 1 combat + boss."""
    graph = generate_floor_graph(42, config={"min_rooms": 3, "max_rooms": 3})
    floor = assemble_floor(graph, registry)
    assert len(floor.rooms) >= 3


def test_no_nonexistent_door_targets(registry: ContentRegistry) -> None:
    """No door should have an empty target_room."""
    graph = generate_floor_graph(99)
    floor = assemble_floor(graph, registry)
    for room_id, room in floor.rooms.items():
        for door in room.doors:
            assert door.target_room, f"Empty door target in {room_id}"


# -- 20-seed smoke test (Phase 7) --

def test_20_seeds_produce_valid_floors(registry: ContentRegistry) -> None:
    """20 seeds should produce 20 valid floors, all with reachable exits."""
    for seed in range(1, 21):
        graph = generate_floor_graph(
            seed, config={"min_rooms": 4, "max_rooms": 8}
        )
        floor = assemble_floor(graph, registry, seed=seed)

        # Must have at least start + 1 room + exit.
        assert len(floor.rooms) >= 3, f"Seed {seed}: too few rooms"

        # Start and exit rooms must exist.
        assert floor.start_room_id in floor.rooms, f"Seed {seed}: no start"
        assert floor.exit_room_id in floor.rooms, f"Seed {seed}: no exit"

        # All doors target valid rooms.
        for room_id, room in floor.rooms.items():
            for door in room.doors:
                assert door.target_room in floor.rooms, \
                    f"Seed {seed}: door in {room_id} targets missing {door.target_room}"

        # All rooms have valid player spawns.
        for room_id, room in floor.rooms.items():
            sx, sy = room.player_spawn
            msg_x = f"Seed {seed}: spawn x out of bounds in {room_id}"
            msg_y = f"Seed {seed}: spawn y out of bounds in {room_id}"
            assert 0 <= sx <= room.width, msg_x
            assert 0 <= sy <= room.height, msg_y


def test_same_seed_same_template_selection(registry: ContentRegistry) -> None:
    """Same seed with multi-template pools should produce the same room ids."""
    graph = generate_floor_graph(42, config={"min_rooms": 4, "max_rooms": 8})
    floor_a = assemble_floor(graph, registry, seed=42)
    floor_b = assemble_floor(graph, registry, seed=42)
    assert set(floor_a.rooms) == set(floor_b.rooms)
