"""The player entity: composition root for stats, body, boxes, and state.

Responsibilities stay isolated (no monolithic Player):

- input translation -> player_controller.PlayerController (intent)
- movement math     -> physics.movement.KinematicBody (data-driven)
- collision data    -> physics Hitbox/Hurtbox components (layers + masks)
- state transitions -> player_state machine (core.state_machine)
- aim/facing        -> set externally by scene-level AimController (policy)
- dodge charges     -> dodge_charges.DodgeCharges (reusable service)
- configuration     -> player_stats.PlayerStats (every value from data files)

Combat (Phase 4) and abilities (Phase 8) attach through entity components
and the event bus - Player gains no god-class duties (RULES.md section 12).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from core.events import EventBus
from engine.entity import Entity
from gameplay.player.dodge_charges import DodgeCharges
from gameplay.player.player_controller import PlayerIntent
from gameplay.player.player_state import PlayerState, build_player_state_machine
from gameplay.player.player_stats import PlayerStats
from physics.collision import CollisionWorld
from physics.hitbox import Hitbox
from physics.hurtbox import Hurtbox
from physics.movement import Direction8, KinematicBody

EVENT_STATE_CHANGED = "player_state_changed"
EVENT_DODGE = "player_dodge"


@dataclass(frozen=True)
class AnimationPose:
    """Render-facing animation hook (Phase 3 spec: hooks exist before sprites).

    Clip naming convention ("idle_down", "dodge_up_right", ...) is settled
    so the sprite pipeline targets it.
    """

    state: PlayerState
    facing: Direction8

    @property
    def clip_name(self) -> str:
        return f"{self.state.value}_{self.facing.name.lower()}"


class Player:
    """Class-agnostic player: coordinates its components each frame."""

    def __init__(
        self,
        stats: PlayerStats,
        x: float = 0.0,
        y: float = 0.0,
        events: EventBus | None = None,
    ) -> None:
        self.stats = stats
        self._events = events
        self.entity = Entity(name="player")
        self.body = self.entity.add(
            KinematicBody(x=x, y=y, width=stats.body_width, height=stats.body_height)
        )
        self.hitbox = self.entity.add(
            Hitbox(
                width=stats.hitbox_width,
                height=stats.hitbox_height,
                offset_x=stats.hitbox_offset_x,
                offset_y=stats.hitbox_offset_y,
            )
        )
        self.hurtbox = self.entity.add(
            Hurtbox(
                width=stats.hurtbox_width,
                height=stats.hurtbox_height,
                offset_x=stats.hurtbox_offset_x,
                offset_y=stats.hurtbox_offset_y,
            )
        )
        self.health = stats.max_health
        self.mana = stats.max_mana

        # Aim/facing is set externally (scene-level AimController).
        self._aim_vector: tuple[float, float] = (0.0, 1.0)  # default: down

        # Movement direction (independent from aim/facing, pre-Phase-4 req).
        self._movement_direction: Direction8 | None = None

        # Dodge charge system (independent per-charge cooldown).
        self.dodge_charges = DodgeCharges(
            max_charges=stats.dodge_max_charges, cooldown=stats.dodge_cooldown
        )

        # State machine.
        self._machine = build_player_state_machine()
        self._dodge_elapsed = 0.0
        self._dodge_direction: tuple[float, float] = (0.0, 1.0)
        self._iframe_remaining = 0.0

    # -- Properties: aim / facing / direction separation --

    @property
    def aim_vector(self) -> tuple[float, float]:
        """Continuous aim vector; set externally by the scene."""
        return self._aim_vector

    @property
    def aim_direction(self) -> Direction8:
        """Aim quantized to 8-direction (for animation/combat)."""
        return Direction8.from_vector(*self._aim_vector)

    @property
    def facing(self) -> Direction8:
        """Visual facing = aim direction (movement never overwrites)."""
        return self.aim_direction

    @property
    def movement_direction(self) -> Direction8 | None:
        """Current movement direction (None when idling)."""
        return self._movement_direction

    def set_aim(self, aim_x: float, aim_y: float) -> None:
        """Set aim externally (scene-level AimController calls per frame)."""
        self._aim_vector = (aim_x, aim_y)

    # -- Properties: state queries --

    @property
    def state(self) -> PlayerState:
        current = self._machine.current
        if current is None:  # pragma: no cover
            raise RuntimeError("player state machine has no active state")
        return PlayerState(current)

    @property
    def animation_pose(self) -> AnimationPose:
        return AnimationPose(state=self.state, facing=self.facing)

    # -- Per-frame update --

    def update(self, intent: PlayerIntent, world: CollisionWorld, dt: float) -> None:
        """Advance player: charge regen -> state logic -> integration."""
        if self.state is PlayerState.DEAD:
            return  # placeholder: Phase 4 fills death handling.
        self.dodge_charges.update(dt)
        if self.state is PlayerState.HIT:
            pass  # placeholder: hit-stun arrives with combat (Phase 4).
        elif self.state is PlayerState.DODGE:
            self._update_dodge(intent, dt)
        else:
            self._update_grounded(intent, dt)
        self.body.integrate(world, dt)
        self.hurtbox.vulnerable = not self.invulnerable

    def _update_grounded(self, intent: PlayerIntent, dt: float) -> None:
        """IDLE/MOVE: dodge > else; charge consumed only on successful dodge."""
        if intent.dodge_pressed and self.dodge_charges.consume():
            self._start_dodge(intent)
            self._update_dodge(intent, dt)
            return
        if intent.wish_x != 0.0 or intent.wish_y != 0.0:
            self._movement_direction = Direction8.from_vector(
                intent.wish_x, intent.wish_y
            )
            self._set_state(PlayerState.MOVE)
        else:
            self._movement_direction = None
            self._set_state(PlayerState.IDLE)
        self.body.accelerate(
            intent.wish_x,
            intent.wish_y,
            self.stats.move_speed,
            self.stats.acceleration,
            self.stats.friction,
            dt,
        )

    def _start_dodge(self, intent: PlayerIntent) -> None:
        """Begin a roll: consume charge, set velocity, start i-frame window."""
        if intent.wish_x != 0.0 or intent.wish_y != 0.0:
            length = math.hypot(intent.wish_x, intent.wish_y)
            self._dodge_direction = (intent.wish_x / length, intent.wish_y / length)
        else:
            self._dodge_direction = self._aim_vector
        dir_len = math.hypot(*self._dodge_direction)
        if dir_len > 0.0:
            self._dodge_direction = (
                self._dodge_direction[0] / dir_len,
                self._dodge_direction[1] / dir_len,
            )
        else:
            self._dodge_direction = (0.0, 1.0)
        self._dodge_elapsed = 0.0
        self._iframe_remaining = self.stats.dodge_invulnerability
        self._movement_direction = Direction8.from_vector(*self._dodge_direction)
        self.body.set_velocity(
            self._dodge_direction[0] * self.stats.roll_speed,
            self._dodge_direction[1] * self.stats.roll_speed,
        )
        self._set_state(PlayerState.DODGE)
        if self._events is not None:
            self._events.publish(
                EVENT_DODGE,
                x=self.body.x,
                y=self.body.y,
                direction=self._dodge_direction,
            )

    def _update_dodge(self, intent: PlayerIntent, dt: float) -> None:
        """Maintain roll velocity; input is ignored until the roll ends."""
        self._dodge_elapsed += dt
        self._iframe_remaining = max(0.0, self._iframe_remaining - dt)
        self.body.set_velocity(
            self._dodge_direction[0] * self.stats.roll_speed,
            self._dodge_direction[1] * self.stats.roll_speed,
        )
        if self._dodge_elapsed >= self.stats.roll_duration:
            if intent.wish_x != 0.0 or intent.wish_y != 0.0:
                self._set_state(PlayerState.MOVE)
            else:
                self._set_state(PlayerState.IDLE)

    def _set_state(self, state: PlayerState) -> None:
        if self.state is state:
            return
        previous = self.state
        self._machine.set_state(state.value)
        if self._events is not None:
            self._events.publish(
                EVENT_STATE_CHANGED, old=previous.value, new=state.value
            )

    # -- Lifecycle --

    def reset(self) -> None:
        """Restore run-start resources (death, new run)."""
        self.health = self.stats.max_health
        self.mana = self.stats.max_mana
        self.dodge_charges.reset()
        self._aim_vector = (0.0, 1.0)
        self._movement_direction = None
        self._machine.set_state(PlayerState.IDLE.value)
        self._dodge_elapsed = 0.0
        self._iframe_remaining = 0.0

    @property
    def alive(self) -> bool:
        return self.state is not PlayerState.DEAD

    @property
    def invulnerable(self) -> bool:
        """True while dodge i-frames remain (Phase 4 adds other sources)."""
        return self._iframe_remaining > 0.0