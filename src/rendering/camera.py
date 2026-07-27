"""Reusable follow camera (rendering layer, framework-free math).

- Smooth exponential follow: framerate-independent, no springs or magic.
- Pixel-perfect output: world->screen transforms round to whole pixels, so
  the image never samples between pixels (both rect corners are rounded,
  keeping on-screen sizes stable frame to frame).
- Configurable zoom (config/display.yaml; PROVISIONAL until the internal
  resolution design decision lands - EXPERIENCE_DESIGN.md section 3).
- Screen shake hook: ``shake_offset`` is a screen-space offset future
  systems drive (Phase 3 ships the hook, not the shake policy).
- Bounds clamping supports future locked arenas (boss rooms): the view
  never scrolls outside the room.
"""

from __future__ import annotations

import math

from physics.collision import AABB
from rendering.renderer import Rect


class Camera:
    """A 2D camera centered on a world position, rendering to a viewport."""

    def __init__(
        self,
        viewport_size: tuple[int, int],
        zoom: float = 1.0,
        follow_stiffness: float = 8.0,
        bounds: AABB | None = None,
    ) -> None:
        if zoom <= 0.0:
            raise ValueError("camera zoom must be positive")
        self._viewport_width, self._viewport_height = viewport_size
        self.zoom = float(zoom)
        self.follow_stiffness = float(follow_stiffness)
        self.x = 0.0  # world position at the screen center
        self.y = 0.0
        self.shake_offset: tuple[float, float] = (0.0, 0.0)  # future shake hook
        self._bounds = bounds

    @property
    def bounds(self) -> AABB | None:
        return self._bounds

    def set_bounds(self, bounds: AABB | None) -> None:
        """Limit the visible area (room bounds now, boss arenas later)."""
        self._bounds = bounds
        self._clamp_to_bounds()

    def center_on(self, x: float, y: float) -> None:
        """Snap instantly to a target (spawns, room transitions)."""
        self.x = x
        self.y = y
        self._clamp_to_bounds()

    def follow(self, target_x: float, target_y: float, dt: float) -> None:
        """Ease toward the target with exponential smoothing.

        The blend factor ``1 - exp(-stiffness * dt)`` is exact for any dt,
        so follow feel is identical at any frame rate.
        """
        blend = 1.0 - math.exp(-self.follow_stiffness * dt)
        self.x += (target_x - self.x) * blend
        self.y += (target_y - self.y) * blend
        self._clamp_to_bounds()

    def world_to_screen(self, world_x: float, world_y: float) -> tuple[int, int]:
        """World point -> integer screen pixel (pixel-perfect rounding)."""
        screen_x = (world_x - self.x) * self.zoom + self._viewport_width / 2.0
        screen_y = (world_y - self.y) * self.zoom + self._viewport_height / 2.0
        return (
            round(screen_x + self.shake_offset[0]),
            round(screen_y + self.shake_offset[1]),
        )

    def screen_rect(self, box: AABB) -> Rect:
        """World box -> integer screen rect; both corners rounded (stable)."""
        left, top = self.world_to_screen(box.left, box.top)
        right, bottom = self.world_to_screen(box.right, box.bottom)
        return (left, top, right - left, bottom - top)

    def screen_to_world(self, screen_x: float, screen_y: float) -> tuple[float, float]:
        """Inverse of world_to_screen: a screen pixel -> world position.

        Camera shake is subtracted before the transformation so mouse-aim
        stays consistent when the screen shakes.
        """
        world_x = (
            screen_x
            - self.shake_offset[0]
            - self._viewport_width / 2.0
        ) / self.zoom + self.x
        world_y = (
            screen_y
            - self.shake_offset[1]
            - self._viewport_height / 2.0
        ) / self.zoom + self.y
        return (world_x, world_y)

    def _clamp_to_bounds(self) -> None:
        """Keep the viewport inside bounds; center if the view is larger."""
        if self._bounds is None:
            return
        half_width = self._viewport_width / (2.0 * self.zoom)
        half_height = self._viewport_height / (2.0 * self.zoom)
        center_x, center_y = self._bounds.center
        if self._bounds.width >= 2.0 * half_width:
            self.x = min(
                max(self.x, self._bounds.left + half_width),
                self._bounds.right - half_width,
            )
        else:
            self.x = center_x
        if self._bounds.height >= 2.0 * half_height:
            self.y = min(
                max(self.y, self._bounds.top + half_height),
                self._bounds.bottom - half_height,
            )
        else:
            self.y = center_y
