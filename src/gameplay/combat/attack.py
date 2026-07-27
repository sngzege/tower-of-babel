"""Attack executor: manages the attack lifecycle.

Phases: windup -> active -> recovery -> cooldown.
Attack execution is data-driven: timing, damage, hitbox shape, and status
tags come from AttackData. The executor produces a ``hitbox_active`` signal
during the active window — the combat system picks up active hitboxes and
resolves them against hurtboxes each frame.

States:
  idle       — attack can be triggered
  windup     — pre-attack delay (no hitbox)
  active     — hitbox is live (can hit enemies)
  recovery   — post-attack delay (no hitbox, no action)
  cooldown   — minimum time before attack can be triggered again

Usage:
    executor = AttackExecutor(attack_data)
    if executor.trigger():       # start windup
        ...
    executor.update(dt)          # advance lifecycle
    if executor.hitbox_active(): # get current hitbox geometry
        hitbox = executor.hitbox_for(owner_x, owner_y)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from physics.collision import AABB, CollisionLayer


class AttackPhase(Enum):
    """Phases of a single attack execution."""

    IDLE = "idle"
    WINDUP = "windup"
    ACTIVE = "active"
    RECOVERY = "recovery"
    COOLDOWN = "cooldown"


@dataclass(frozen=True)
class AttackData:
    """Data-driven attack parameters (from data files).

    ``id`` — unique identifier.
    ``windup`` — seconds before the hitbox becomes active (can be 0.0).
    ``active`` — seconds the hitbox remains live.
    ``recovery`` — seconds after active before the entity can act again.
    ``cooldown`` — minimum seconds before the attack can be triggered again.
    ``damage`` — base damage value.
    ``damage_types`` — type tags for damage pipeline (e.g. 'physical').
    ``hitbox_width/height/offset`` — hitbox geometry relative to owner center.
    ``knockback_x/y`` — push applied to target on hit.
    ``status_tags`` — status effect tags to apply on hit.
    ``layer`` — which collision layer the temporary hitbox belongs to.
    ``target_layers`` — which hurtbox layers this attack can hit.
    """

    id: str = "default_attack"
    windup: float = 0.0
    active: float = 0.15
    recovery: float = 0.1
    cooldown: float = 0.3
    damage: float = 10.0
    damage_types: frozenset[str] = frozenset({"physical"})
    hitbox_width: float = 24.0
    hitbox_height: float = 20.0
    hitbox_offset_x: float = 0.0
    hitbox_offset_y: float = 0.0
    knockback_x: float = 0.0
    knockback_y: float = 0.0
    status_tags: frozenset[str] = frozenset()
    layer: str = CollisionLayer.PLAYER_HITBOX.value
    target_layers: frozenset[str] = frozenset({CollisionLayer.ENEMY_HURTBOX.value})


@dataclass
class AttackState:
    """Current runtime state of an attack executor."""

    phase: AttackPhase = AttackPhase.IDLE
    elapsed: float = 0.0


class AttackExecutor:
    """Manages one attack's lifecycle.

    AttackExecutors are composable: a player or enemy can have several
    (one per ability). The owning system triggers them and reads hitbox
    state each frame.
    """

    def __init__(self, data: AttackData) -> None:
        self.data = data
        self.state = AttackState()

    # -- Triggers --

    def trigger(self) -> bool:
        """Start the attack if idle/ready. Returns True if the attack started."""
        if self.state.phase is not AttackPhase.IDLE:
            return False
        self.state = AttackState(phase=AttackPhase.WINDUP, elapsed=0.0)
        return True

    def cancel(self) -> None:
        """Cancel the current attack immediately."""
        self.state = AttackState()

    # -- Update --

    def update(self, dt: float) -> AttackPhase:
        """Advance the attack lifecycle by ``dt``.

        Returns the current phase after the update. The owning system should
        call this every frame while the attack is active, and continue until
        IDLE is returned (the attack is fully complete).
        """
        if self.state.phase is AttackPhase.IDLE:
            return AttackPhase.IDLE

        self.state.elapsed += dt
        phase = self.state.phase

        if phase is AttackPhase.WINDUP and self.state.elapsed >= self.data.windup:
            self.state.phase = AttackPhase.ACTIVE
            self.state.elapsed = 0.0

        elif phase is AttackPhase.ACTIVE and self.state.elapsed >= self.data.active:
            self.state.phase = AttackPhase.RECOVERY
            self.state.elapsed = 0.0

        elif phase is AttackPhase.RECOVERY and self.state.elapsed >= self.data.recovery:
            if self.data.cooldown > 0.0:
                self.state.phase = AttackPhase.COOLDOWN
                self.state.elapsed = 0.0
            else:
                self.state.phase = AttackPhase.IDLE

        elif phase is AttackPhase.COOLDOWN and self.state.elapsed >= self.data.cooldown:
            self.state.phase = AttackPhase.IDLE

        return self.state.phase

    # -- Queries --

    def can_trigger(self) -> bool:
        """True if the attack can be triggered right now."""
        return self.state.phase is AttackPhase.IDLE

    def hitbox_active(self) -> bool:
        """True if the hitbox is currently live (can hit enemies)."""
        return self.state.phase is AttackPhase.ACTIVE

    def hitbox_for(
        self,
        owner_x: float,
        owner_y: float,
        *,
        facing_x: float = 0.0,
        facing_y: float = 0.0,
    ) -> AABB | None:
        """Get the world-space hitbox AABB if the hitbox is active.

        The hitbox is offset in the facing direction, so attacks hit
        in front of the entity.
        """
        if not self.hitbox_active():
            return None

        # Hitbox center is purely along the facing direction.
        # No absolute offset — the hitbox follows where you aim.
        push = self.data.hitbox_height * 0.5
        center_x = owner_x + facing_x * push
        center_y = owner_y + facing_y * push

        return AABB(
            center_x - self.data.hitbox_width / 2.0,
            center_y - self.data.hitbox_height / 2.0,
            self.data.hitbox_width,
            self.data.hitbox_height,
        )
