"""Stage configuration and assembled stage data (Phase 7).

A stage is an ordered sequence of procedurally generated floors, fully
described by data (data/world/stages/*.yaml, schema: stage.schema.yaml):

  Stage Data → StageConfig → StageData (floors: FloorData[])

The runtime never hardcodes stage structure: main.py loads a stage document
from the ContentRegistry, parses it into a StageConfig, and generates the
stage through the seeded pipeline (stage_generator).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from world.floor_assembler import FloorData


class StageConfigError(ValueError):
    """Raised when a stage document is missing or malformed."""


@dataclass(frozen=True)
class StageConfig:
    """Parsed configuration from a stage data document.

    ``floor_count`` floors are generated; each floor uses the shared room
    bounds (``min_rooms``/``max_rooms`` spine rooms) and ``branch_chance``.
    ``room_kinds`` optionally overrides the generator's side-branch kind
    weights (only relevant when ``branch_chance`` > 0).
    """

    stage_id: str
    name: str
    index: int
    floor_count: int
    min_rooms: int
    max_rooms: int
    branch_chance: float = 0.0
    room_kinds: dict[str, float] | None = None
    tags: tuple[str, ...] = ()

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> StageConfig:
        """Build a config from a data/world/stages document; raise on problems."""
        source = str(document.get("id", "<unknown>"))
        problems: list[str] = []

        stage_id = document.get("id")
        if not isinstance(stage_id, str) or not stage_id:
            problems.append("'id' must be a non-empty string")
            stage_id = source
        name = document.get("name")
        if not isinstance(name, str) or not name:
            problems.append("'name' must be a non-empty string")
            name = stage_id
        raw_index = document.get("index")
        if isinstance(raw_index, bool) or not isinstance(raw_index, int):
            problems.append("'index' must be an int")
            raw_index = 0

        floors = document.get("floors")
        if not isinstance(floors, dict):
            problems.append("'floors' must be a mapping")
            floors = {}

        def read_int(node: Any, path: str, default: int) -> int:
            if isinstance(node, bool) or not isinstance(node, int):
                problems.append(f"'{path}' must be an int")
                return default
            return node

        floor_count = read_int(floors.get("count"), "floors.count", 0)
        min_rooms = read_int(floors.get("min_rooms"), "floors.min_rooms", 3)
        max_rooms = read_int(floors.get("max_rooms"), "floors.max_rooms", 3)

        raw_branch = floors.get("branch_chance", 0.0)
        if isinstance(raw_branch, bool) or not isinstance(raw_branch, (int, float)):
            problems.append("'floors.branch_chance' must be a number")
            raw_branch = 0.0
        branch_chance = float(raw_branch)

        if floor_count < 1:
            problems.append("'floors.count' must be >= 1")
        if min_rooms < 3:
            problems.append("'floors.min_rooms' must be >= 3")
        if max_rooms < min_rooms:
            problems.append("'floors.max_rooms' must be >= 'floors.min_rooms'")
        if not 0.0 <= branch_chance <= 1.0:
            problems.append("'floors.branch_chance' must be within [0, 1]")

        raw_kinds = document.get("room_kinds")
        room_kinds: dict[str, float] | None = None
        if raw_kinds is not None:
            if not isinstance(raw_kinds, dict):
                problems.append("'room_kinds' must be a mapping of kind → weight")
            else:
                room_kinds = {}
                for kind, weight in raw_kinds.items():
                    if isinstance(weight, bool) or not isinstance(weight, (int, float)):
                        problems.append(f"'room_kinds.{kind}' must be a number")
                        continue
                    room_kinds[str(kind)] = float(weight)

        raw_tags = document.get("tags", [])
        tags = tuple(str(tag) for tag in raw_tags) if isinstance(raw_tags, list) else ()

        if problems:
            raise StageConfigError(
                "invalid stage document '"
                + source
                + "': "
                + "; ".join(sorted(set(problems)))
            )

        return cls(
            stage_id=stage_id,
            name=name,
            index=raw_index,
            floor_count=floor_count,
            min_rooms=min_rooms,
            max_rooms=max_rooms,
            branch_chance=branch_chance,
            room_kinds=room_kinds,
            tags=tags,
        )


@dataclass(frozen=True)
class StageData:
    """One assembled stage: ordered floors ready for traversal."""

    config: StageConfig
    seed: int | str
    floors: tuple[FloorData, ...] = field(default_factory=tuple)

    @property
    def floor_count(self) -> int:
        return len(self.floors)
