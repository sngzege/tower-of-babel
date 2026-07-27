"""Player controller: translates abstract input frames into player intents.

This is the ONLY player-side module that sees ``ActionFrame``. It is
stateless and framework-free; all device/binding knowledge stays in
src/input.

``PlayerIntent`` carries separate channels for movement, combat actions,
and future abilities (approved pre-Phase-4 architecture). Aim direction is
resolved externally by ``AimController`` (which owns the priority policy) -
the controller never couples to rendering/camera internals.
"""

from __future__ import annotations

from dataclasses import dataclass

from input.input_manager import Action, ActionFrame
from physics.movement import clamp_magnitude

# The set of action names that become ``ability_pressed`` (combat Phase 4+).
_ABILITY_ACTIONS = frozenset(
    {
        Action.CLASS_SKILL,
        Action.SKILL_1,
        Action.SKILL_2,
        Action.ULTIMATE,
        Action.AURA,
    }
)


@dataclass(frozen=True)
class PlayerIntent:
    """What the player wants this frame.

    Movement and combat are fully independent channels. The aim vector is
    set directly on the Player by the scene-level AimController, so the
    controller never needs camera/rendering knowledge.
    """

    wish_x: float = 0.0
    wish_y: float = 0.0
    dodge_pressed: bool = False
    primary_attack_pressed: bool = False
    primary_attack_held: bool = False
    ability_pressed: frozenset[Action] = frozenset()


class PlayerController:
    """Maps ActionFrame -> PlayerIntent (diagonal-safe, analog-aware)."""

    def build_intent(self, frame: ActionFrame) -> PlayerIntent:
        wish_x, wish_y = clamp_magnitude(frame.move_x, frame.move_y)
        return PlayerIntent(
            wish_x=wish_x,
            wish_y=wish_y,
            dodge_pressed=Action.DODGE in frame.pressed,
            primary_attack_pressed=Action.PRIMARY_ATTACK in frame.pressed,
            primary_attack_held=Action.PRIMARY_ATTACK in frame.held,
            ability_pressed=frozenset(
                a for a in frame.pressed if a in _ABILITY_ACTIONS
            ),
        )
