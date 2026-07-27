"""The player entity: composition root for stats, body, boxes, and state.

Responsibilities stay isolated per the Phase 3 spec (no monolithic Player):

- input translation -> player_controller.PlayerController (ActionFrame -> intent)
- movement math     -> physics.movement.KinematicBody (data-driven parameters)
- collision data    -> physics Hitbox/Hurtbox components (layers + masks)
- state transitions -> player_state machine (core.state_machine)
- configuration     -> player_stats.PlayerStats (every value from data files)

Player itself only COORDINATES these pieces per frame. Combat (Phase 4) and
abilities (Phase 8) attach through the entity components and the event bus -
Player gains no god-class duties (RULES.md section 12).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from core.events import EventBus
from engine.entity import Entity
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

    The sprite/animation pipeline (later phase) maps ``clip_name`` to real
    clips; the greybox renderer only tints by state. Clip naming convention
    ("idle_down", "dodge_up_right", ...) is fixed now so assets target it.
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
        # Runtime resources (max values come from data; combat mutates these).
        self.health = stats.max_health
        self.mana = stats.max_mana
        self.facing = Direction8.DOWN
        self._machine = build_player_state_machine()
        self._dodge_elapsed = 0.0
        self._dodge_direction = Direction8.DOWN.vector
        self._iframe_remaining = 0.0

    @property
    def state(self) -> PlayerState:
        current = self._machine.current
        if current is None:  # pragma: no cover - machine always has a state
            raise RuntimeError("player state machine has no active state")
        return PlayerState(current)

    @property
    def alive(self) -> bool:
        return self.state is not PlayerState.DEAD

    @property
    def invulnerable(self) -> bool:
        """True while dodge i-frames remain (Phase 4 adds other sources)."""
        return self._iframe_remaining > 0.0

    @property
    def animation_pose(self) -> AnimationPose:
        return AnimationPose(state=self.state, facing=self.facing)

    def update(self, intent: PlayerIntent, world: CollisionWorld, dt: float) -> None:
        """Advance the player by one frame: state logic, then integration."""
        if self.state is PlayerState.DEAD:
            return  # placeholder: death handling arrives with combat (Phase 4)
        if self.state is PlayerState.HIT:
            pass  # placeholder: hit-stun logic arrives with combat (Phase 4)
        elif self.state is PlayerState.DODGE:
            self._update_dodge(intent, dt)
        else:
            self._update_grounded(intent, dt)
        self.body.integrate(world, dt)
        self.hurtbox.vulnerable = not self.invulnerable

    def _update_grounded(self, intent: PlayerIntent, dt: float) -> None:
        """IDLE/MOVE: dodge takes priority, otherwise data-driven movement."""
        if intent.dodge_pressed:
            self._start_dodge(intent)
            # The starting frame counts: the roll moves and ages immediately.
            self._update_dodge(intent, dt)
            return
        if intent.wish_x != 0.0 or intent.wish_y != 0.0:
            self.facing = Direction8.from_vector(intent.wish_x, intent.wish_y)
            self._set_state(PlayerState.MOVE)
        else:
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
        """Begin a roll: fixed velocity, fixed duration, i-frame window."""
        if intent.wish_x != 0.0 or intent.wish_y != 0.0:
            length = math.hypot(intent.wish_x, intent.wish_y)
            self._dodge_direction = (intent.wish_x / length, intent.wish_y / length)
        else:
            self._dodge_direction = self.facing.vector
        self._dodge_elapsed = 0.0
        self._iframe_remaining = self.stats.dodge_invulnerability
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
        """Roll at constant speed; input is ignored until the roll ends."""
        self._dodge_elapsed += dt
        self._iframe_remaining = max(0.0, self._iframe_remaining - dt)
        self.body.set_velocity(
            self._dodge_direction[0] * self.stats.roll_speed,
            self._dodge_direction[1] * self.stats.roll_speed,
        )
        if self._dodge_elapsed >= self.stats.roll_duration:
            # Keep exit velocity so the roll slides out smoothly; grounded
            # logic re-takes control next frame.
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
