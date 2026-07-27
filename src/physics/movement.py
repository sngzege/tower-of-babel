"""Kinematic movement math and the movement component (framework-free).

Pure integration helpers (``approach``, ``clamp_magnitude``), the 8-way
``Direction8`` vocabulary, and ``KinematicBody`` - the component that gives
an entity a position, velocity, and collision box.

No gameplay policy lives here: speed, acceleration, and friction arrive as
parameters from data-driven stats. Sprint support is architectural only - a
future system simply passes a higher ``max_speed`` (Phase 3 spec).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from engine.component import Component
from physics.collision import AABB, CollisionLayer, CollisionResult, CollisionWorld


def approach(value: float, target: float, delta: float) -> float:
    """Move ``value`` toward ``target`` by at most ``delta`` (no overshoot)."""
    if value < target:
        return min(value + delta, target)
    return max(value - delta, target)


def clamp_magnitude(x: float, y: float, maximum: float = 1.0) -> tuple[float, float]:
    """Scale (x, y) so its length never exceeds ``maximum`` (diagonal-safe).

    Vectors shorter than ``maximum`` keep their length, so analog sticks
    preserve partial-tilt (variable speed) input.
    """
    length = math.hypot(x, y)
    if length == 0.0 or length <= maximum:
        return (x, y)
    scale = maximum / length
    return (x * scale, y * scale)


class Direction8(Enum):
    """8-way facing in screen space (+x right, +y down); vectors are unit."""

    RIGHT = (1.0, 0.0)
    DOWN_RIGHT = (math.sqrt(0.5), math.sqrt(0.5))
    DOWN = (0.0, 1.0)
    DOWN_LEFT = (-math.sqrt(0.5), math.sqrt(0.5))
    LEFT = (-1.0, 0.0)
    UP_LEFT = (-math.sqrt(0.5), -math.sqrt(0.5))
    UP = (0.0, -1.0)
    UP_RIGHT = (math.sqrt(0.5), -math.sqrt(0.5))

    @property
    def vector(self) -> tuple[float, float]:
        """Unit vector pointing along this direction."""
        return self.value

    @classmethod
    def from_vector(cls, x: float, y: float) -> Direction8:
        """Nearest 8-way direction for a nonzero vector."""
        if x == 0.0 and y == 0.0:
            raise ValueError("zero vector has no direction")
        octant = round(math.atan2(y, x) / (math.pi / 4.0)) % 8
        return _OCTANT_DIRECTIONS[octant]


_OCTANT_DIRECTIONS: tuple[Direction8, ...] = (
    Direction8.RIGHT,
    Direction8.DOWN_RIGHT,
    Direction8.DOWN,
    Direction8.DOWN_LEFT,
    Direction8.LEFT,
    Direction8.UP_LEFT,
    Direction8.UP,
    Direction8.UP_RIGHT,
)


@dataclass
class KinematicBody(Component):
    """Position, velocity, and collision box of a moving entity.

    Coordinates are the box CENTER in world pixels - gameplay thinks in
    entity positions, boxes are derived for physics.
    """

    x: float
    y: float
    width: float
    height: float
    vx: float = 0.0
    vy: float = 0.0
    collide_layers: tuple[CollisionLayer, ...] = (CollisionLayer.WORLD,)

    @property
    def box(self) -> AABB:
        return AABB(
            self.x - self.width / 2.0,
            self.y - self.height / 2.0,
            self.width,
            self.height,
        )

    @property
    def speed(self) -> float:
        return math.hypot(self.vx, self.vy)

    def teleport(self, x: float, y: float) -> None:
        """Place the body and discard all velocity (spawns, room transitions)."""
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0

    def accelerate(
        self,
        wish_x: float,
        wish_y: float,
        max_speed: float,
        acceleration: float,
        friction: float,
        dt: float,
    ) -> None:
        """Steer velocity toward the wish direction with data-driven feel.

        ``wish`` is a magnitude-limited vector (0..1): its direction steers,
        its magnitude scales the target speed (analog partial tilt = slower).
        With no input, friction decays velocity to a full stop.
        """
        if wish_x != 0.0 or wish_y != 0.0:
            self.vx = approach(self.vx, wish_x * max_speed, acceleration * dt)
            self.vy = approach(self.vy, wish_y * max_speed, acceleration * dt)
        else:
            self.vx = approach(self.vx, 0.0, friction * dt)
            self.vy = approach(self.vy, 0.0, friction * dt)

    def set_velocity(self, vx: float, vy: float) -> None:
        """Directly set velocity (dodge rolls and knockback drive the body)."""
        self.vx = vx
        self.vy = vy

    def integrate(self, world: CollisionWorld, dt: float) -> CollisionResult:
        """Move by velocity * dt against the world; stop on contacted axes."""
        result = world.move_and_slide(
            self.box, self.vx * dt, self.vy * dt, layers=self.collide_layers
        )
        self.x, self.y = result.box.center
        if result.hit_x:
            self.vx = 0.0
        if result.hit_y:
            self.vy = 0.0
        return result
