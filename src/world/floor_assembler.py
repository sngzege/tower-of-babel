"""Floor assembler: converts a FloorGraph into playable connected rooms.

Flow:
  Seed → FloorGraph (dungeon_generator)
       → FloorAssembler.assemble(graph, registry)
       → FloorData (all rooms, connections, start/exit)
       → RoomManager + PlaytestScene

Phase 6 established the basic assembly pipeline.
Phase 7 adds:
  - Seeded template selection (multiple candidates per kind)
  - Encounter population per room
  - Reusable kind→template config for stage data
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from core.content_registry import ContentRegistry
from utils.random_utils import Rng
from world.dungeon_generator import FloorGraph, RoomNode
from world.room import Door, Room

# Default template pool per graph node kind.
# Multiple candidates → seeded random selection for variety.
# Extend this as new room templates are created.
_KIND_TO_TEMPLATES: dict[str, list[str]] = {
    "start": ["greybox_start"],
    "combat": ["greybox_room"],
    "boss": ["greybox_exit"],
    "elite": ["greybox_room"],
    "rest": ["greybox_room"],
    "shop": ["greybox_room"],
    "event": ["greybox_room"],
    "shrine": ["greybox_room"],
    "secret": ["greybox_room"],
}

# Enemy selection per room kind.
# Maps kind → list of (enemy_id, count) tuples.
# Phase 7 greybox: only combat rooms get enemies.
_KIND_TO_ENEMIES: dict[str, list[tuple[str, int]]] = {
    "combat": [("greybox_dummy", 2)],
    "elite": [("greybox_dummy", 3)],
}


@dataclass(frozen=True)
class FloorData:
    """One assembled floor: all rooms, connections, and entry/exit points.

    ``rooms`` maps room_id → Room.
    ``start_room_id`` is where the player spawns.
    ``exit_room_id`` is the floor exit (boss room).
    ``connections`` maps room_id → list of (door, target_room_id) tuples
    for rooms reachable from that room.
    """

    rooms: dict[str, Room]
    start_room_id: str
    exit_room_id: str
    connections: dict[str, list[tuple[Door, str]]] = field(default_factory=dict)


class FloorAssemblyError(Exception):
    """Raised when a floor cannot be assembled (missing template, bad graph)."""


def _room_id_for(node: RoomNode) -> str:
    """Derive a room id from a graph node uid."""
    return f"room_{node.uid}"


def _assign_room_ids(
    graph: FloorGraph,
    kind_to_templates: dict[str, list[str]],
    rng: Rng,
) -> dict[int, str]:
    """Map each node uid → template id, with seeded selection from candidates.

    Unknown kinds fall back to combat template list.
    """
    mapping: dict[int, str] = {}
    for uid, node in graph.rooms.items():
        candidates = kind_to_templates.get(node.kind)
        if not candidates:
            candidates = kind_to_templates.get("combat", ["greybox_room"])
        template = rng.choice(candidates)
        mapping[uid] = template
    return mapping


def _build_room(
    registry: ContentRegistry,
    template_id: str,
    room_id: str,
) -> Room:
    """Load a template document and build a Room with the given id."""
    document: dict[str, Any] = deepcopy(registry.get("world", template_id))
    document["id"] = room_id
    return Room.from_document(document)


def _wire_doors(
    graph: FloorGraph,
    uid_to_template: dict[int, str],
    uid_to_room_id: dict[int, str],
    registry: ContentRegistry,
) -> tuple[dict[str, Room], dict[str, list[tuple[Door, str]]]]:
    """Build all rooms and wire their doors based on graph links.

    Returns (rooms, connections).
    """
    rooms: dict[str, Room] = {}
    connections: dict[str, list[tuple[Door, str]]] = {}

    # Phase 1: Build all rooms from templates.
    for uid, node in graph.rooms.items():
        template_id = uid_to_template[uid]
        room_id = uid_to_room_id[uid]
        room = _build_room(registry, template_id, room_id)
        rooms[room_id] = room
        connections[room_id] = []

    # Phase 2: Wire doors based on graph links.
    for uid, node in graph.rooms.items():
        room_id = uid_to_room_id[uid]
        room = rooms[room_id]

        # For each link to another node, create a matching door.
        linked_doors: list[Door] = []
        for linked_uid in node.links:
            linked_room_id = uid_to_room_id[linked_uid]

            # Find a door slot in this room that matches the direction.
            # For the greybox, rooms have standard door positions:
            #   - Right-side door (x > 900): exit to next room
            #   - Left-side door (x < 50): entry from previous room
            #
            # The graph is undirected, but rooms have directional doors.
            # Determine whether the linked room is "ahead" or "behind"
            # based on depth (deeper = further in the floor).
            linked_depth = graph.rooms[linked_uid].depth
            is_ahead = linked_depth > node.depth

            matched = False
            for door in room.doors:
                door_is_right = door.box.x > 900.0
                door_is_left = door.box.x < 50.0

                # Right door = exit to deeper room.
                if is_ahead and door_is_right:
                    linked_doors.append(
                        Door(
                            box=door.box,
                            target_room=linked_room_id,
                            target_spawn=door.target_spawn,
                        )
                    )
                    matched = True
                    break

                # Left door = entry from shallower room.
                if not is_ahead and door_is_left:
                    linked_doors.append(
                        Door(
                            box=door.box,
                            target_room=linked_room_id,
                            target_spawn=door.target_spawn,
                        )
                    )
                    matched = True
                    break

            if matched:
                connections[room_id].append(
                    (linked_doors[-1], linked_room_id)
                )

        # Replace doors with the wired subset.
        rooms[room_id] = Room(
            room_id=room.room_id,
            kind=room.kind,
            width=room.width,
            height=room.height,
            player_spawn=room.player_spawn,
            solids=room.solids,
            doors=tuple(linked_doors),
        )

    return rooms, connections


def assemble_floor(
    graph: FloorGraph,
    registry: ContentRegistry,
    seed: int = 42,
    kind_to_templates: dict[str, list[str]] | None = None,
    kind_to_enemies: dict[str, list[tuple[str, int]]] | None = None,
) -> FloorData:
    """Assemble a FloorGraph into a FloorData with connected rooms.

    Args:
        graph: The logical floor layout.
        registry: ContentRegistry with 'world' category loaded.
        seed: Deterministic seed for template selection.
        kind_to_templates: Optional override for kind→template pool mapping.
        kind_to_enemies: Optional override for kind→enemy list mapping.

    Returns:
        FloorData with all rooms wired and ready for traversal.
    """
    kt = dict(kind_to_templates or _KIND_TO_TEMPLATES)
    # kind_to_enemies will be used when encounter population is wired into rooms.

    # Seeded RNG for reproducible template selection.
    rng = Rng(seed)

    # Map each node uid to its template id.
    uid_to_template = _assign_room_ids(graph, kt, rng)
    uid_to_room_id = {uid: _room_id_for(graph.rooms[uid]) for uid in graph.rooms}

    rooms, connections = _wire_doors(graph, uid_to_template, uid_to_room_id, registry)

    start_room_id = _room_id_for(graph.rooms[graph.start_uid])
    exit_room_id = _room_id_for(graph.rooms[graph.boss_uid])

    return FloorData(
        rooms=rooms,
        start_room_id=start_room_id,
        exit_room_id=exit_room_id,
        connections=connections,
    )
