"""Floor assembler: converts a FloorGraph into playable connected rooms.

Flow:
  Seed → FloorGraph (dungeon_generator)
       → FloorAssembler.assemble(graph, registry)
       → FloorData (all rooms, connections, encounters, start/exit)
       → RoomManager / StageManager + PlaytestScene

Phase 6 established the basic assembly pipeline.
Phase 7 adds:
  - Seeded template selection from multi-template pools per kind
  - Encounter resolution per room (template override → kind default)
  - Floor-exit door: the exit room's right door targets FLOOR_EXIT_TARGET,
    which the StageManager interprets as "advance to the next floor"
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from core.content_registry import ContentRegistry
from utils.random_utils import Rng
from world.dungeon_generator import FloorGraph, RoomNode
from world.room import Door, Room

# Door target used for the floor exit in the deepest room of a floor.
# The StageManager advances to the next floor (or completes the stage)
# when the player walks through a door with this target.
FLOOR_EXIT_TARGET = "@floor_exit"

# Default template pool per graph node kind.
# Multiple candidates → seeded random selection for variety.
# Extend this as new room templates are created.
_KIND_TO_TEMPLATES: dict[str, list[str]] = {
    "start": ["greybox_start", "greybox_start_b"],
    "combat": ["greybox_room", "greybox_combat_hall", "greybox_combat_pillars"],
    "boss": ["greybox_boss_arena"],
    "elite": ["greybox_combat_pillars"],
    "rest": ["greybox_room"],
    "shop": ["greybox_room"],
    "event": ["greybox_combat_hall"],
    "shrine": ["greybox_room"],
    "secret": ["greybox_combat_hall"],
}

# Enemy selection per room kind (fallback default).
# Maps kind → list of (enemy_id, count) tuples. A room template carrying an
# explicit ``encounter`` key overrides these defaults (Phase 7 greybox).
_KIND_TO_ENEMIES: dict[str, list[tuple[str, int]]] = {
    "combat": [("greybox_dummy", 2)],
    "elite": [("greybox_dummy", 3)],
}


@dataclass(frozen=True)
class FloorData:
    """One assembled floor: all rooms, connections, and entry/exit points.

    ``rooms`` maps room_id → Room.
    ``start_room_id`` is where the player spawns.
    ``exit_room_id`` is the floor exit (boss room); its right door targets
    FLOOR_EXIT_TARGET.
    ``connections`` maps room_id → list of (door, target_room_id) tuples
    for rooms reachable from that room (room→room edges only; the floor
    exit is discoverable via the exit room's doors).
    ``encounters`` maps room_id → ((enemy_id, count), ...) population data.
    ``templates`` maps room_id → template id used to build the room.
    """

    rooms: dict[str, Room]
    start_room_id: str
    exit_room_id: str
    connections: dict[str, list[tuple[Door, str]]] = field(default_factory=dict)
    encounters: dict[str, tuple[tuple[str, int], ...]] = field(default_factory=dict)
    templates: dict[str, str] = field(default_factory=dict)


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


def _resolve_encounter(
    document: dict[str, Any],
    node_kind: str,
    kind_to_enemies: dict[str, list[tuple[str, int]]],
) -> tuple[tuple[str, int], ...]:
    """Resolve a room's enemy population.

    A template document carrying an explicit ``encounter`` key wins
    (even an empty list → no enemies); otherwise the kind default applies.
    """
    if "encounter" in document:
        resolved: list[tuple[str, int]] = []
        raw = document.get("encounter") or []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            enemy_id = str(entry.get("enemy", ""))
            count = int(entry.get("count", 1))
            if enemy_id and count > 0:
                resolved.append((enemy_id, count))
        return tuple(resolved)
    return tuple(kind_to_enemies.get(node_kind, ()))


def _build_rooms(
    graph: FloorGraph,
    uid_to_template: dict[int, str],
    uid_to_room_id: dict[int, str],
    registry: ContentRegistry,
    kind_to_enemies: dict[str, list[tuple[str, int]]],
) -> tuple[dict[str, Room], dict[str, tuple[tuple[str, int], ...]]]:
    """Build all rooms from templates and resolve their encounters."""
    rooms: dict[str, Room] = {}
    encounters: dict[str, tuple[tuple[str, int], ...]] = {}
    for uid, node in graph.rooms.items():
        template_id = uid_to_template[uid]
        room_id = uid_to_room_id[uid]
        document: dict[str, Any] = deepcopy(registry.get("world", template_id))
        document["id"] = room_id
        rooms[room_id] = Room.from_document(document)
        encounters[room_id] = _resolve_encounter(document, node.kind, kind_to_enemies)
    return rooms, encounters


def _wire_doors(
    graph: FloorGraph,
    rooms: dict[str, Room],
    uid_to_room_id: dict[int, str],
) -> tuple[dict[str, Room], dict[str, list[tuple[Door, str]]]]:
    """Wire room doors based on graph links; add the floor-exit door.

    For the greybox, rooms have standard door slots:
      - Right-side door (x > 900): exit to a deeper room / the floor exit
      - Left-side door (x < 50): entry from a shallower room

    Each link claims one free slot of the matching direction; links without
    a free slot (e.g. side branches on a two-slot template) stay graph-only.
    The deepest room's right slot becomes the floor exit (FLOOR_EXIT_TARGET).

    Returns (wired_rooms, connections).
    """
    wired_rooms: dict[str, Room] = {}
    connections: dict[str, list[tuple[Door, str]]] = {}

    for uid, node in graph.rooms.items():
        room_id = uid_to_room_id[uid]
        room = rooms[room_id]
        connections[room_id] = []

        # The graph is undirected, but rooms have directional doors.
        # "Ahead" = deeper in the floor. Sorted for deterministic slot claims.
        linked_doors: list[Door] = []
        used_slots: set[int] = set()
        for linked_uid in sorted(node.links):
            linked_room_id = uid_to_room_id[linked_uid]
            is_ahead = graph.rooms[linked_uid].depth > node.depth

            for slot, door in enumerate(room.doors):
                if slot in used_slots:
                    continue
                door_is_right = door.box.x > 900.0
                door_is_left = door.box.x < 50.0
                if (is_ahead and not door_is_right) or (
                    not is_ahead and not door_is_left
                ):
                    continue
                linked_doors.append(
                    Door(
                        box=door.box,
                        target_room=linked_room_id,
                        target_spawn=door.target_spawn,
                    )
                )
                used_slots.add(slot)
                connections[room_id].append((linked_doors[-1], linked_room_id))
                break

        # Floor exit: the deepest room's right door slot leads out of the floor.
        if uid == graph.boss_uid:
            exit_slot = next(
                (
                    slot
                    for slot, door in enumerate(room.doors)
                    if door.box.x > 900.0 and slot not in used_slots
                ),
                None,
            )
            if exit_slot is None:
                raise FloorAssemblyError(
                    f"exit room '{room_id}' has no free right-side door slot "
                    "for the floor exit"
                )
            slot_door = room.doors[exit_slot]
            linked_doors.append(
                Door(
                    box=slot_door.box,
                    target_room=FLOOR_EXIT_TARGET,
                    target_spawn=slot_door.target_spawn,
                )
            )

        # Replace doors with the wired subset.
        wired_rooms[room_id] = Room(
            room_id=room.room_id,
            kind=room.kind,
            width=room.width,
            height=room.height,
            player_spawn=room.player_spawn,
            solids=room.solids,
            doors=tuple(linked_doors),
            enemy_spawns=room.enemy_spawns,
        )

    return wired_rooms, connections


def assemble_floor(
    graph: FloorGraph,
    registry: ContentRegistry,
    seed: int | str = 42,
    kind_to_templates: dict[str, list[str]] | None = None,
    kind_to_enemies: dict[str, list[tuple[str, int]]] | None = None,
) -> FloorData:
    """Assemble a FloorGraph into a FloorData with connected rooms.

    Args:
        graph: The logical floor layout.
        registry: ContentRegistry with 'world' category loaded.
        seed: Deterministic seed for template selection.
        kind_to_templates: Optional override for kind→template pool mapping.
        kind_to_enemies: Optional override for kind→enemy list mapping
            (templates with an explicit 'encounter' key always win).

    Returns:
        FloorData with all rooms wired and ready for traversal.
    """
    kt = dict(kind_to_templates or _KIND_TO_TEMPLATES)
    ke = dict(kind_to_enemies or _KIND_TO_ENEMIES)

    # Seeded RNG for reproducible template selection.
    rng = Rng(seed)

    # Map each node uid to its template id.
    uid_to_template = _assign_room_ids(graph, kt, rng)
    uid_to_room_id = {uid: _room_id_for(graph.rooms[uid]) for uid in graph.rooms}

    rooms, encounters = _build_rooms(
        graph, uid_to_template, uid_to_room_id, registry, ke
    )
    rooms, connections = _wire_doors(graph, rooms, uid_to_room_id)

    start_room_id = _room_id_for(graph.rooms[graph.start_uid])
    exit_room_id = _room_id_for(graph.rooms[graph.boss_uid])
    templates = {
        uid_to_room_id[uid]: template for uid, template in uid_to_template.items()
    }

    return FloorData(
        rooms=rooms,
        start_room_id=start_room_id,
        exit_room_id=exit_room_id,
        connections=connections,
        encounters=encounters,
        templates=templates,
    )
