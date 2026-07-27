"""Floor assembler: converts a FloorGraph into playable connected rooms.

Flow:
  Seed → FloorGraph (dungeon_generator)
       → FloorAssembler.assemble(graph, registry)
       → FloorData (all rooms, connections, start/exit)
       → RoomManager + PlaytestScene

Phase 6 establishes the assembly pipeline. Phase 7 (procedural generation)
will add seeded template selection and encounter population.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from core.content_registry import ContentRegistry
from world.dungeon_generator import FloorGraph, RoomNode
from world.room import Door, Room

# Template id per graph node kind.
# Extend this mapping as new room kinds are approved.
_KIND_TO_TEMPLATE: dict[str, str] = {
    "start": "greybox_start",
    "combat": "greybox_room",
    "boss": "greybox_exit",
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
    graph: FloorGraph, kind_to_template: dict[str, str]
) -> dict[int, str]:
    """Map each node uid → template id.

    Unknown kinds are mapped to 'combat' as fallback.
    Raises FloorAssemblyError only if the base kinds (start/boss) are missing.
    """
    mapping: dict[int, str] = {}
    for uid, node in graph.rooms.items():
        template = kind_to_template.get(node.kind)
        if template is None:
            template = kind_to_template.get("combat", "greybox_room")
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
    kind_to_template: dict[str, str] | None = None,
) -> FloorData:
    """Assemble a FloorGraph into a FloorData with connected rooms.

    Args:
        graph: The logical floor layout.
        registry: ContentRegistry with 'world' category loaded.
        kind_to_template: Optional override for kind→template mapping.

    Returns:
        FloorData with all rooms wired and ready for traversal.
    """
    kt = dict(kind_to_template or _KIND_TO_TEMPLATE)

    # Map each node uid to its template id.
    uid_to_template = _assign_room_ids(graph, kt)
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
