"""Procedural floor-graph prototype.

Generates an abstract floor layout as a graph of typed rooms. The graph is
deliberately navigation-model agnostic (design decision D7 is unresolved): a
free-roam floor can be built from the same adjacency graph as a node-map route.

Guarantees:
- Deterministic per seed (utils.random_utils.Rng).
- A path always exists from the start room to the boss room.
- Side branches are optional typed rooms hanging off the main path.

PROVISIONAL: room kinds and generator parameters are generic placeholders
awaiting the stage data schema and the human developer's dungeon design.
No gameplay content is defined here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from utils.random_utils import Rng

START = "start"
BOSS = "boss"
COMBAT = "combat"

_DEFAULT_OPTIONAL_KINDS = {"elite": 1.0, "event": 1.0, "shop": 1.0, "rest": 1.0}


@dataclass
class RoomNode:
    uid: int
    kind: str
    depth: int
    links: set[int] = field(default_factory=set)


@dataclass
class FloorGraph:
    rooms: dict[int, RoomNode]
    start_uid: int
    boss_uid: int

    def path_exists(self) -> bool:
        """Breadth-first check that the boss is reachable from the start."""
        seen = {self.start_uid}
        stack = [self.start_uid]
        while stack:
            current = stack.pop()
            if current == self.boss_uid:
                return True
            for nxt in self.rooms[current].links:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return False


def generate_floor_graph(
    seed: int | str, config: dict[str, Any] | None = None
) -> FloorGraph:
    """Generate one floor graph.

    Config keys (all optional, PROVISIONAL defaults):
      min_rooms / max_rooms: spine room-count bounds (>= 3).
      branch_chance: probability that each spine room grows one side room.
      optional_kinds: {kind: weight} for side rooms.
    """
    cfg = dict(config or {})
    min_rooms = int(cfg.get("min_rooms", 6))
    max_rooms = int(cfg.get("max_rooms", 9))
    if min_rooms < 3 or max_rooms < min_rooms:
        raise ValueError("room bounds must satisfy 3 <= min_rooms <= max_rooms")
    branch_chance = float(cfg.get("branch_chance", 0.4))
    optional_kinds = dict(cfg.get("optional_kinds", _DEFAULT_OPTIONAL_KINDS))

    rng = Rng(seed)
    total = rng.int_range(min_rooms, max_rooms)
    rooms: dict[int, RoomNode] = {}

    # Spine: guaranteed start -> ... -> boss path.
    rooms[0] = RoomNode(uid=0, kind=START, depth=0)
    spine: list[int] = [0]
    for uid in range(1, total - 1):
        rooms[uid] = RoomNode(uid=uid, kind=COMBAT, depth=uid)
        rooms[spine[-1]].links.add(uid)
        rooms[uid].links.add(spine[-1])
        spine.append(uid)
    boss_uid = total - 1
    rooms[boss_uid] = RoomNode(uid=boss_uid, kind=BOSS, depth=boss_uid)
    rooms[spine[-1]].links.add(boss_uid)
    rooms[boss_uid].links.add(spine[-1])

    # Branches: optional typed side rooms hanging off the spine.
    next_uid = total
    kinds = list(optional_kinds)
    weights = [optional_kinds[kind] for kind in kinds]
    for spine_uid in spine[1:]:
        if optional_kinds and rng.chance(branch_chance):
            kind = rng.weighted_choice(kinds, weights)
            rooms[next_uid] = RoomNode(
                uid=next_uid, kind=kind, depth=rooms[spine_uid].depth
            )
            rooms[next_uid].links.add(spine_uid)
            rooms[spine_uid].links.add(next_uid)
            next_uid += 1

    return FloorGraph(rooms=rooms, start_uid=0, boss_uid=boss_uid)
