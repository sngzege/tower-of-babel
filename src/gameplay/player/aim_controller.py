"""Aim controller: resolves mouse-vs-keyboard aim priority into a single vector.

PURE LOGIC — no framework imports, no pygame. The policy is deterministic
and documented:

1. If the mouse pointer has moved since the previous frame (``pointer_moved``),
   mouse aim becomes the active aim source.
2. If a keyboard/gamepad directional aim axis is non-zero (arrows, right stick),
   keyboard aim becomes the active aim source.
3. If both changed in the same frame, keyboard aim takes priority (last input
   wins — the player just let go of the mouse and pressed an arrow key).
4. If neither has new input, the previous aim direction is retained.
5. When mouse aim is active, the pointer is converted to a world-direction
   vector via the camera callback.

Architecture allows this priority rule to be swapped without touching Player
or Combat (just replace AimController or override _resolve).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from input.input_manager import ActionFrame
from physics.movement import clamp_magnitude


@dataclass(frozen=True)
class AimResult:
    """Resolved aim state for this frame."""

    direction: tuple[float, float]
    source: str  # "keyboard" | "mouse" | "held"


class AimController:
    """Resolves one frame of input into a single aim direction vector.

    ``screen_to_world`` is a callback into the Camera (set externally so
    AimController never depends on rendering internals).
    """

    def __init__(
        self,
        screen_to_world: Callable[[float, float], tuple[float, float]],
    ) -> None:
        self._screen_to_world = screen_to_world
        self._current_dir: tuple[float, float] = (0.0, -1.0)  # default: up
        self._current_source: str = "held"

    def resolve(
        self, frame: ActionFrame, player_world_x: float, player_world_y: float
    ) -> AimResult:
        """Determine the single aim direction for this frame."""
        aim_x, aim_y = clamp_magnitude(frame.aim_x, frame.aim_y)

        # Keyboard aim axis is non-zero → switch to keyboard mode.
        if aim_x != 0.0 or aim_y != 0.0:
            self._current_dir = (aim_x, aim_y)
            self._current_source = "keyboard"
        # Mouse pointer moved → switch to mouse mode (world-space direction).
        elif frame.pointer_moved and frame.pointer is not None:
            wx, wy = self._screen_to_world(*frame.pointer)
            dx = wx - player_world_x
            dy = wy - player_world_y
            length = math.hypot(dx, dy)
            if length > 4.0:  # ignore tiny jitter near the player center
                self._current_dir = (dx / length, dy / length)
                self._current_source = "mouse"
        # Otherwise: retain previous direction and source.

        return AimResult(direction=self._current_dir, source=self._current_source)

    def reset_facing(
        self, default_direction: tuple[float, float] = (0.0, -1.0)
    ) -> None:
        """Reset to a default direction (spawn, room transition)."""
        self._current_dir = default_direction
        self._current_source = "held"
