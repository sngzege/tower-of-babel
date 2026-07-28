"""The player entity: composition root for stats, body, boxes, and state.

Responsibilities stay isolated (no monolithic Player):

- input translation -> player_controller.PlayerController (intent)
- movement math     -> physics.movement.KinematicBody (data-driven)
- collision data    -> physics Hitbox/Hurtbox components (layers + masks)
- state transitions -> player_state machine (core.state_machine)
- aim/facing        -> set externally by scene-level AimController (policy)
- dodge charges     -> dodge_charges.DodgeCharges (reusable service)
- combat            -> AttackExecutor + InvulnerabilityService
                        + StatusEffectManager (Phase 4)
- configuration     -> player_stats.PlayerStats (every value from data files)

Combat (Phase 4) attaches through entity components and the event bus —
Player gains no god-class duties (RULES.md section 12).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from core.events import EventBus
from engine.entity import Entity
from gameplay.combat.attack import AttackData, AttackExecutor
from gameplay.combat.invulnerability import InvulnerabilityService
from gameplay.combat.status_effects import StatusEffectManager
from gameplay.player.dodge_charges import DodgeCharges
from gameplay.player.player_controller import PlayerIntent
from gameplay.player.player_state import PlayerState, build_player_state_machine
from gameplay.player.player_stats import PlayerStats
from gameplay.builds.ability import AbilityData, AbilityExecutor, AbilitySlot
from physics.collision import CollisionWorld
from physics.hitbox import Hitbox
from physics.hurtbox import Hurtbox
from physics.movement import Direction8, KinematicBody

EVENT_STATE_CHANGED = "player_state_changed"
EVENT_DODGE = "player_dodge"


@dataclass(frozen=True)
class AnimationPose:
    """Render-facing animation hook (Phase 3 spec: hooks exist before sprites)."""

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
        attack_data: AttackData | None = None,
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

        # Phase 4 combat components.
        self.invuln_service = InvulnerabilityService(on_state_changed=lambda v: None)
        self.status_manager = StatusEffectManager()
        # Use provided AttackData or fall back to hardcoded defaults.
        if attack_data is not None:
            final_attack = AttackData(
                id=attack_data.id,
                windup=attack_data.windup,
                active=attack_data.active,
                recovery=attack_data.recovery,
                cooldown=(
                    attack_data.cooldown
                    if attack_data.cooldown > 0
                    else stats.attack_speed
                ),
                damage=attack_data.damage,
                damage_types=attack_data.damage_types,
                hitbox_spread=attack_data.hitbox_spread,
                hitbox_reach=attack_data.hitbox_reach,
            )
        else:
            final_attack = AttackData(
                id="default_attack",
                windup=0.0,
                active=0.12,
                recovery=0.05,
                cooldown=stats.attack_speed,
                damage=25.0,
                damage_types=frozenset({"physical"}),
                hitbox_spread=16.0,
                hitbox_reach=36.0,
            )
        self.attack_executor = AttackExecutor(final_attack)

        # Ability executors (Q/E/R/T) — initially empty, populated by build.
        self.ability_executors: dict[str, AbilityExecutor] = {
            AbilitySlot.SKILL_Q.value: AbilityExecutor(
                AbilityData(id="empty_q", name="Empty", cooldown=999.0)
            ),
            AbilitySlot.SKILL_E.value: AbilityExecutor(
                AbilityData(id="empty_e", name="Empty", cooldown=999.0)
            ),
            AbilitySlot.SKILL_R.value: AbilityExecutor(
                AbilityData(id="empty_r", name="Empty", cooldown=999.0)
            ),
            AbilitySlot.AURA.value: AbilityExecutor(
                AbilityData(id="empty_t", name="Empty", cooldown=999.0)
            ),
        }
        self._ability_slot_map: dict[str, str] = {
            "skill_1": AbilitySlot.SKILL_Q.value,
            "skill_2": AbilitySlot.SKILL_E.value,
            "ultimate": AbilitySlot.SKILL_R.value,
            "aura": AbilitySlot.AURA.value,
        }

        # State machine.
        self._machine = build_player_state_machine()
        self._dodge_elapsed = 0.0
        self._dodge_direction: tuple[float, float] = (0.0, 1.0)
        self._hitstun_remaining: float = 0.0
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
        """Advance: charge regen -> invulnerability -> attack -> state logic."""
        if self.state is PlayerState.DEAD:
            return
        self.dodge_charges.update(dt)
        self.invuln_service.update(dt)

        # Handle attack intent.
        if intent.primary_attack_pressed:
            self.attack_executor.trigger()
        self.attack_executor.update(dt)

        # Handle ability intents.
        for action_name in intent.ability_pressed:
            slot_key = self._ability_slot_map.get(action_name.value if hasattr(action_name, 'value') else str(action_name))
            if slot_key and slot_key in self.ability_executors:
                self.ability_executors[slot_key].activate()
        for executor in self.ability_executors.values():
            executor.update(dt)

        if self.state is PlayerState.HIT:
            self._update_hit(intent, dt)
        elif self.state is PlayerState.DODGE:
            self._update_dodge(intent, dt)
        else:
            self._update_grounded(intent, dt)
        self.body.integrate(world, dt)
        self.hurtbox.vulnerable = not self.invuln_service.invulnerable

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
        """Begin a roll: consume charge, set velocity, add invulnerability source."""
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
        self.invuln_service.add("dodge", self.stats.dodge_invulnerability)
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
        self.body.set_velocity(
            self._dodge_direction[0] * self.stats.roll_speed,
            self._dodge_direction[1] * self.stats.roll_speed,
        )
        if self._dodge_elapsed >= self.stats.roll_duration:
            if intent.wish_x != 0.0 or intent.wish_y != 0.0:
                self._set_state(PlayerState.MOVE)
            else:
                self._set_state(PlayerState.IDLE)

    def _update_hit(self, intent: PlayerIntent, dt: float) -> None:
        """Hitstun: no input response. Once timer expires, return to move/idle."""
        self._hitstun_remaining = max(0.0, self._hitstun_remaining - dt)
        self.body.vx = 0.0
        self.body.vy = 0.0
        if self._hitstun_remaining <= 0.0:
            if self.state is PlayerState.DEAD:
                return
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
        self.invuln_service.clear()
        self.status_manager.clear()
        self._aim_vector = (0.0, 1.0)
        self._movement_direction = None
        self._dodge_elapsed = 0.0
        self._hitstun_remaining = 0.0
        self._set_state(PlayerState.IDLE)

    @property
    def alive(self) -> bool:
        return self.state is not PlayerState.DEAD

    @property
    def invulnerable(self) -> bool:
        """True while any invulnerability source is active (dodge, hitstun, etc.)."""
        return self.invuln_service.invulnerable

    # -- Hitstun timer --

    def set_hitstun(self, duration: float) -> None:
        """Set a hitstun timer that keeps the player in HIT state.

        The player processes this in _update_hit(), which returns to
        IDLE/MOVE once the timer expires.
        """
        self._hitstun_remaining = duration

    # -- Combat reactions --

    def on_hit(self, hitstun_duration: float = 0.15) -> None:
        """Called when the player takes damage from an attack.

        Transitions to HIT state (skipped if dead or mid-dodge).
        Refreshes the hitstun timer even if already in HIT state.
        The caller should also check if health <= 0 and call die().
        """
        if self.state is PlayerState.DEAD or self.state is PlayerState.DODGE:
            return
        if self.state is not PlayerState.HIT:
            self._set_state(PlayerState.HIT)
        self.set_hitstun(hitstun_duration)

    def die(self) -> None:
        """Handle player death."""
        if self.state is PlayerState.DEAD:
            return
        self._set_state(PlayerState.DEAD)
