"""Hitbox: the offensive collision box of an attack or damaging body.

Phase 3 ships the component and geometry only; the damage pipeline that
consumes hitboxes arrives with combat in Phase 4 (IMPLEMENTATION_PLAN.md).
Layers and target masks are declarative data, never hardcoded checks, so
enemies reuse this component unchanged (future enemy compatibility).
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.component import Component
from physics.collision import AABB, CollisionLayer


@dataclass
class Hitbox(Component):
    """Offensive box, positioned relative to its owner's center.

    ``layer`` says what this box is; ``targets`` says which layers it can
    hit (the combat system filters overlaps by mask in Phase 4).
    """

    width: float
    height: float
    offset_x: float = 0.0
    offset_y: float = 0.0
    layer: CollisionLayer = CollisionLayer.PLAYER_HITBOX
    targets: tuple[CollisionLayer, ...] = (CollisionLayer.ENEMY_HURTBOX,)
    enabled: bool = True

    def box_at(self, center_x: float, center_y: float) -> AABB:
        """World-space box for an owner centered at (center_x, center_y)."""
        return AABB(
            center_x + self.offset_x - self.width / 2.0,
            center_y + self.offset_y - self.height / 2.0,
            self.width,
            self.height,
        )
