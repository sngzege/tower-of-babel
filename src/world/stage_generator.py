"""Stage generation: StageConfig → StageData (Phase 7).

Each floor gets its own deterministic seed derived from the stage seed, so:
  - Same stage seed → same logical stage structure (all floors).
  - Same floor seed → same logical floor structure.
  - Different seeds → potentially different valid floors/templates.

No global random state is touched; everything flows through utils.random_utils.Rng
(via generate_floor_graph and assemble_floor).
"""

from __future__ import annotations

from typing import Any

from core.content_registry import ContentRegistry
from world.dungeon_generator import FloorGraph, RoomNode, generate_floor_graph
from world.floor_assembler import FloorData, assemble_floor
from world.stage import StageConfig, StageData


def floor_seed_for(stage_seed: int | str, stage_id: str, floor_index: int) -> str:
    """Derive the deterministic seed for one floor of a stage."""
    return f"{stage_seed}:{stage_id}:floor:{floor_index}"


def generate_stage(
    config: StageConfig,
    registry: ContentRegistry,
    seed: int | str,
) -> StageData:
    """Generate every floor of a stage from its configuration.

    Args:
        config: Parsed stage configuration (floor count, room bounds, ...).
        registry: ContentRegistry with 'world' (rooms) and 'enemies' loaded.
        seed: Stage seed; per-floor seeds are derived deterministically.

    Returns:
        StageData with ``config.floor_count`` assembled floors plus
        a boss floor appended at the end.
    """
    floors = []
    for index in range(config.floor_count):
        floor_seed = floor_seed_for(seed, config.stage_id, index)
        graph_config: dict[str, Any] = {
            "min_rooms": config.min_rooms,
            "max_rooms": config.max_rooms,
            "branch_chance": config.branch_chance,
        }
        if config.room_kinds:
            graph_config["optional_kinds"] = dict(config.room_kinds)
        graph = generate_floor_graph(floor_seed, config=graph_config)
        floors.append(assemble_floor(graph, registry, seed=floor_seed))

    # Append a boss floor.
    boss_seed = floor_seed_for(seed, config.stage_id, config.floor_count)
    boss_floor = _generate_boss_floor(boss_seed, registry)
    floors.append(boss_floor)

    return StageData(config=config, seed=seed, floors=tuple(floors))


def _generate_boss_floor(
    seed: int | str,
    registry: ContentRegistry,
) -> FloorData:
    """Generate a single-room boss floor.

    The boss floor contains one 'boss' room with a boss encounter
    (first_boss). The room's exit door uses FLOOR_EXIT_TARGET so the
    StageManager advances to stage_complete when the player exits
    after defeating the boss.
    """

    # Build a minimal FloorGraph with one boss room.
    boss_node = RoomNode(uid=0, kind="boss", depth=0)
    graph = FloorGraph(
        rooms={0: boss_node},
        start_uid=0,
        boss_uid=0,
    )

    boss_floor = assemble_floor(graph, registry, seed=seed)

    # Add boss encounter data.
    boss_floor.encounters[boss_floor.exit_room_id] = (("first_boss", 1),)

    return boss_floor
