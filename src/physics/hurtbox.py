"""Hurtbox: the vulnerable collision box of a damageable entity.

Phase 3 ships the component, geometry, and the ``vulnerable`` flag that
dodge i-frames drive; the damage pipeline that queries hurtboxes arrives
with combat in Phase 4 (IMPLEMENTATION_PLAN.md). Layers and source masks
are declarative data, never hardcoded checks, so enemies reuse this
component unchanged (future enemy compatibility).
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.component import Component
from physics.collision import AABB, CollisionLayer


@dataclass
class Hurtbox(Component):
    """Vulnerable box, positioned relative to its owner's center.

    ``layer`` says what this box is; ``sources`` says which hitbox layers
    may damage it (the combat system filters overlaps by mask in Phase 4).
    ``vulnerable=False`` means hits pass through (dodge i-frames now; the
    Phase 4 invulnerability system will drive further sources of this flag).
    """

    width: float
    height: float
    offset_x: float = 0.0
    offset_y: float = 0.0
    layer: CollisionLayer = CollisionLayer.PLAYER_HURTBOX
    sources: tuple[CollisionLayer, ...] = (CollisionLayer.ENEMY_HITBOX,)
    enabled: bool = True
    vulnerable: bool = True

    def box_at(self, center_x: float, center_y: float) -> AABB:
        """World-space box for an owner centered at (center_x, center_y)."""
        return AABB(
            center_x + self.offset_x - self.width / 2.0,
            center_y + self.offset_y - self.height / 2.0,
            self.width,
            self.height,
        )
