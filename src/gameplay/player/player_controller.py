"""Player controller: translates abstract input frames into player intents.

This is the ONLY player-side module that sees ``ActionFrame``. It is
stateless and framework-free; all device/binding knowledge stays in
src/input. Combat-era actions (attack/skills, L5 layout) will surface here
as additional intent fields - consumers never read input directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from input.input_manager import Action, ActionFrame
from physics.movement import clamp_magnitude


@dataclass(frozen=True)
class PlayerIntent:
    """What the player wants this frame.

    ``wish`` is the movement axis, magnitude-limited to 1: keyboard diagonals
    become unit vectors, analog stick tilt keeps its partial magnitude
    (variable speed). ``dodge_pressed`` is the Space/button edge this frame.
    """

    wish_x: float = 0.0
    wish_y: float = 0.0
    dodge_pressed: bool = False


class PlayerController:
    """Maps ActionFrame -> PlayerIntent (diagonal-safe, analog-aware)."""

    def build_intent(self, frame: ActionFrame) -> PlayerIntent:
        wish_x, wish_y = clamp_magnitude(frame.move_x, frame.move_y)
        return PlayerIntent(
            wish_x=wish_x,
            wish_y=wish_y,
            dodge_pressed=Action.DODGE in frame.pressed,
        )
