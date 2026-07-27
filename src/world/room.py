"""Room: a playable space built from data (Phase 3 greybox scope).

A Room is static geometry plus metadata loaded from data/world/rooms/*.yaml
(schema: data/schemas/room.schema.yaml). Phase 3 uses exactly one
hand-authored greybox room to test game feel - no procedural generation.
Room/floor assembly (Phases 6-7) will reuse this type and its collision
hand-off, so the scene never hardcodes geometry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from physics.collision import AABB, CollisionWorld, StaticCollider


class RoomError(ValueError):
    """Raised when a room document is missing or malformed."""


@dataclass(frozen=True)
class Room:
    """Static room geometry in world pixels (origin at top-left corner)."""

    room_id: str
    width: float
    height: float
    player_spawn: tuple[float, float]
    solids: tuple[AABB, ...]

    @property
    def bounds(self) -> AABB:
        return AABB(0.0, 0.0, self.width, self.height)

    def build_collision_world(self) -> CollisionWorld:
        """A collision world containing every solid in the room."""
        return CollisionWorld(StaticCollider(box) for box in self.solids)

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> Room:
        """Build a room from a data/world/rooms document; raise on problems."""
        source = str(document.get("id", "<unknown>"))
        problems: list[str] = []

        def read_number(node: Any, path: str, default: float = 0.0) -> float:
            if isinstance(node, bool) or not isinstance(node, (int, float)):
                problems.append(f"'{path}' must be a number")
                return default
            return float(node)

        size = document.get("size")
        if not isinstance(size, dict):
            problems.append("missing 'size' mapping")
            size = {}
        width = read_number(size.get("width"), "size.width")
        height = read_number(size.get("height"), "size.height")
        if width <= 0.0:
            problems.append("'size.width' must be positive")
        if height <= 0.0:
            problems.append("'size.height' must be positive")

        spawn = document.get("player_spawn")
        if not isinstance(spawn, dict):
            problems.append("missing 'player_spawn' mapping")
            spawn = {}
        spawn_x = read_number(spawn.get("x"), "player_spawn.x")
        spawn_y = read_number(spawn.get("y"), "player_spawn.y")

        raw_solids = document.get("solids", [])
        if not isinstance(raw_solids, list):
            problems.append("'solids' must be a list")
            raw_solids = []
        solids: list[AABB] = []
        for index, entry in enumerate(raw_solids):
            if not isinstance(entry, dict):
                problems.append(f"'solids[{index}]' must be a mapping")
                continue
            solid_width = read_number(entry.get("w"), f"solids[{index}].w")
            solid_height = read_number(entry.get("h"), f"solids[{index}].h")
            if solid_width <= 0.0 or solid_height <= 0.0:
                problems.append(f"'solids[{index}]' must have positive w/h")
            solids.append(
                AABB(
                    read_number(entry.get("x"), f"solids[{index}].x"),
                    read_number(entry.get("y"), f"solids[{index}].y"),
                    solid_width,
                    solid_height,
                )
            )

        if problems:
            raise RoomError(
                f"invalid room document '{source}': "
                + "; ".join(sorted(set(problems)))
            )
        return cls(
            room_id=source,
            width=width,
            height=height,
            player_spawn=(spawn_x, spawn_y),
            solids=tuple(solids),
        )
