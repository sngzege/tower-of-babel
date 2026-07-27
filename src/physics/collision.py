"""Collision primitives: AABBs, collision layers, and the collision world.

Framework-free physics layer (Phase 3). Provides:

- ``AABB``: float axis-aligned boxes used by bodies, hitboxes, and hurtboxes.
- ``CollisionLayer``: the layer vocabulary (world/player/enemy) so movement
  and combat never hardcode "who collides with whom" (future enemy-ready).
- ``CollisionWorld``: static solid geometry (walls, obstacles) with
  axis-separated move-and-slide resolution and overlap queries.

Dynamic hitbox/hurtbox hit resolution (damage) arrives with combat in
Phase 4; boxes already carry layers/masks so that phase needs no redesign.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum


class CollisionLayer(Enum):
    """What a box belongs to; layer filters decide who interacts."""

    WORLD = "world"
    PLAYER_BODY = "player_body"
    PLAYER_HITBOX = "player_hitbox"
    PLAYER_HURTBOX = "player_hurtbox"
    ENEMY_BODY = "enemy_body"
    ENEMY_HITBOX = "enemy_hitbox"
    ENEMY_HURTBOX = "enemy_hurtbox"


@dataclass(frozen=True)
class AABB:
    """Axis-aligned box in world pixels (x/y = top-left corner)."""

    x: float
    y: float
    width: float
    height: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2.0, self.y + self.height / 2.0)

    def moved(self, dx: float, dy: float) -> AABB:
        """A copy offset by (dx, dy)."""
        return AABB(self.x + dx, self.y + dy, self.width, self.height)

    def intersects(self, other: AABB) -> bool:
        """True on any overlap; touching edges do not count as intersecting."""
        return (
            self.left < other.right
            and self.right > other.left
            and self.top < other.bottom
            and self.bottom > other.top
        )


@dataclass(frozen=True)
class StaticCollider:
    """Immovable solid geometry (walls, obstacles)."""

    box: AABB
    layer: CollisionLayer = CollisionLayer.WORLD


@dataclass(frozen=True)
class CollisionResult:
    """Outcome of a move-and-slide: resolved box plus per-axis contact flags."""

    box: AABB
    hit_x: bool = False
    hit_y: bool = False


class CollisionWorld:
    """Static solid geometry with move-and-slide resolution and queries.

    Colliders are plain data (rooms build them); nothing here knows about
    entities or gameplay. Dynamic bodies query/resolve against the statics.
    """

    def __init__(self, colliders: Iterable[StaticCollider] | None = None) -> None:
        self._colliders: list[StaticCollider] = list(colliders or ())

    def add(self, collider: StaticCollider) -> StaticCollider:
        self._colliders.append(collider)
        return collider

    def add_box(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        layer: CollisionLayer = CollisionLayer.WORLD,
    ) -> StaticCollider:
        """Convenience builder for a static box collider."""
        return self.add(StaticCollider(AABB(x, y, width, height), layer))

    def clear(self) -> None:
        self._colliders.clear()

    @property
    def colliders(self) -> tuple[StaticCollider, ...]:
        return tuple(self._colliders)

    def query(
        self,
        box: AABB,
        layers: Iterable[CollisionLayer] | None = None,
    ) -> list[StaticCollider]:
        """All colliders overlapping ``box`` (optionally filtered by layers)."""
        wanted = None if layers is None else set(layers)
        return [
            collider
            for collider in self._colliders
            if (wanted is None or collider.layer in wanted)
            and box.intersects(collider.box)
        ]

    def move_and_slide(
        self,
        box: AABB,
        dx: float,
        dy: float,
        layers: Iterable[CollisionLayer] = (CollisionLayer.WORLD,),
    ) -> CollisionResult:
        """Move ``box`` by (dx, dy), sliding along colliders on ``layers``.

        Axis-separated SWEPT resolution: the box moves on X, then on Y; each
        axis clamps at first contact (flush) so even large steps cannot
        tunnel through thin walls. Contact on an axis is reported so callers
        can zero that velocity component.
        """
        wanted = set(layers)
        solids = [c.box for c in self._colliders if c.layer in wanted]
        resolved, hit_x = _sweep_axis(box, solids, dx, axis=0)
        resolved, hit_y = _sweep_axis(resolved, solids, dy, axis=1)
        return CollisionResult(box=resolved, hit_x=hit_x, hit_y=hit_y)


def _sweep_axis(
    box: AABB, solids: list[AABB], delta: float, axis: int
) -> tuple[AABB, bool]:
    """Move ``box`` along one axis (0=x, 1=y) with swept contact resolution.

    Returns (resolved_box, hit). Walls ahead clamp the displacement at the
    contact point; a box already overlapping is pushed out against its
    motion. ``delta == 0`` is a no-op (never reports contact).
    """
    if delta == 0.0:
        return box, False
    allowed = delta
    hit = False
    for other in solids:
        if axis == 0:
            if not (box.top < other.bottom and box.bottom > other.top):
                continue
            start_edge, end_edge = box.left, box.right
            other_start, other_end = other.left, other.right
        else:
            if not (box.left < other.right and box.right > other.left):
                continue
            start_edge, end_edge = box.top, box.bottom
            other_start, other_end = other.top, other.bottom
        if delta > 0.0:
            if other_start >= end_edge:  # wall ahead: clamp at contact
                contact = other_start - end_edge
                if contact < allowed:
                    allowed, hit = contact, True
            elif other_end > start_edge:  # embedded: push back out
                push = other_start - end_edge
                if push < allowed:
                    allowed, hit = push, True
        else:
            if other_end <= start_edge:  # wall ahead (negative direction)
                contact = other_end - start_edge
                if contact > allowed:
                    allowed, hit = contact, True
            elif other_start < end_edge:  # embedded: push back out
                push = other_end - start_edge
                if push > allowed:
                    allowed, hit = push, True
    moved = box.moved(allowed, 0.0) if axis == 0 else box.moved(0.0, allowed)
    return moved, hit
