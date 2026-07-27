"""Tests for world.dungeon_generator (generic procgen prototype)."""

from __future__ import annotations

import pytest

from world.dungeon_generator import BOSS, START, FloorGraph, generate_floor_graph


def test_boss_always_reachable() -> None:
    for seed in range(25):
        graph = generate_floor_graph(seed)
        assert isinstance(graph, FloorGraph)
        assert graph.path_exists()


def test_deterministic_per_seed() -> None:
    first = generate_floor_graph("same")
    second = generate_floor_graph("same")
    signature_a = [(n.uid, n.kind, sorted(n.links)) for n in first.rooms.values()]
    signature_b = [(n.uid, n.kind, sorted(n.links)) for n in second.rooms.values()]
    assert signature_a == signature_b


def test_room_count_within_bounds() -> None:
    config = {"min_rooms": 5, "max_rooms": 7, "branch_chance": 0.0}
    for seed in range(25):
        graph = generate_floor_graph(seed, config)
        assert 5 <= len(graph.rooms) <= 7


def test_invalid_bounds_raise() -> None:
    with pytest.raises(ValueError):
        generate_floor_graph(0, {"min_rooms": 10, "max_rooms": 5})


def test_start_and_boss_kinds() -> None:
    graph = generate_floor_graph(0)
    assert graph.rooms[graph.start_uid].kind == START
    assert graph.rooms[graph.boss_uid].kind == BOSS
