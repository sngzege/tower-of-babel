"""Greybox enemy entity: composition root for stats, body, hurtbox, and AI.

Follows the same composition pattern as Player (src/gameplay/player/player.py).
Uses the same reusable combat components from Phase 4:
  - AttackExecutor for attacks
  - InvulnerabilityService for invulnerability (hitstun, etc.)
  - DamagePipeline for damage application (via CombatSystem)

This is a TECHNICAL combat target, NOT a production enemy.
No special abilities, no behaviours beyond chase+attack.
Production enemies (Phase 5+) extend the framework established here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from engine.entity import Entity
from gameplay.combat.attack import AttackData, AttackExecutor
from gameplay.combat.invulnerability import InvulnerabilityService
from gameplay.combat.status_effects import StatusEffectManager
from physics.collision import CollisionLayer
from physics.hurtbox import Hurtbox
from physics.movement import KinematicBody

ENEMY_STATE_CHANGED = "enemy_state_changed"
ENEMY_DAMAGED = "enemy_damaged"
ENEMY_KILLED = "enemy_killed"


@dataclass
class EnemyConfig:
    """Parsed configuration from an enemy data document."""

    id: str
    name: str
    max_health: float
    damage: float
    speed: float
    body_width: float = 24.0
    body_height: float = 24.0
    hurtbox_width: float = 22.0
    hurtbox_height: float = 22.0
    hurtbox_offset_x: float = 0.0
    hurtbox_offset_y: float = 0.0
    attack_windup: float = 0.2
    attack_active: float = 0.3
    attack_recovery: float = 0.15
    attack_cooldown: float = 1.5
    attack_damage: float = 10.0
    attack_damage_types: frozenset[str] = frozenset({"physical"})
    attack_hitbox_spread: float = 18.0
    attack_hitbox_reach: float = 20.0
    attack_min_range: float = 20.0
    attack_ideal_range: float = 28.0
    aggro_range: float = 200.0

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> EnemyConfig:
        """Build config from a registry document (enemy/common/*.yaml)."""
        stats = document.get("stats", {})
        body = document.get("body", {})
        hurtbox = document.get("hurtbox", {})
        attack = document.get("attack", {})
        return cls(
            id=document.get("id", "unknown"),
            name=document.get("name", "Unknown"),
            max_health=float(stats.get("health", 50)),
            damage=float(stats.get("damage", 10)),
            speed=float(stats.get("speed", 60.0)),
            body_width=float(body.get("width", 24.0)),
            body_height=float(body.get("height", 24.0)),
            hurtbox_width=float(hurtbox.get("width", 22.0)),
            hurtbox_height=float(hurtbox.get("height", 22.0)),
            hurtbox_offset_x=float(hurtbox.get("offset_x", 0.0)),
            hurtbox_offset_y=float(hurtbox.get("offset_y", 0.0)),
            attack_windup=float(attack.get("windup", 0.2)),
            attack_active=float(attack.get("active", 0.3)),
            attack_recovery=float(attack.get("recovery", 0.15)),
            attack_cooldown=float(attack.get("cooldown", 1.5)),
            attack_damage=float(attack.get("damage", 10.0)),
            attack_damage_types=frozenset(attack.get("damage_types", ["physical"])),
            attack_hitbox_spread=float(attack.get("hitbox_spread", 18.0)),
            attack_hitbox_reach=float(attack.get("hitbox_reach", 20.0)),
            attack_min_range=float(attack.get("min_range", 20.0)),
            attack_ideal_range=float(attack.get("ideal_range", 28.0)),
            aggro_range=float(document.get("aggro_range", 200.0)),
        )


class Enemy:
    """Greybox enemy: composition root.

    Has a body (movement + collision), hurtbox (vulnerable area),
    health, invulnerability, status effects, and attack executor.
    AI (chase + attack) is driven externally by EnemyAI.
    """

    def __init__(
        self,
        config: EnemyConfig,
        x: float = 0.0,
        y: float = 0.0,
    ) -> None:
        self.config = config
        self.entity = Entity(name=config.id)
        self.body = self.entity.add(
            KinematicBody(x=x, y=y, width=config.body_width, height=config.body_height)
        )
        self.hurtbox = self.entity.add(
            Hurtbox(
                width=config.hurtbox_width,
                height=config.hurtbox_height,
                offset_x=config.hurtbox_offset_x,
                offset_y=config.hurtbox_offset_y,
                layer=CollisionLayer.ENEMY_HURTBOX,
                sources=(CollisionLayer.PLAYER_HITBOX,),
            )
        )

        # Combat state.
        self._health = config.max_health
        self.invuln_service = InvulnerabilityService()
        self.status_manager = StatusEffectManager()
        self.attack_executor = AttackExecutor(
            AttackData(
                id=f"{config.id}_attack",
                windup=config.attack_windup,
                active=config.attack_active,
                recovery=config.attack_recovery,
                cooldown=config.attack_cooldown,
                damage=config.attack_damage,
                damage_types=config.attack_damage_types,
                hitbox_spread=config.attack_hitbox_spread,
                hitbox_reach=config.attack_hitbox_reach,
                layer=CollisionLayer.ENEMY_HITBOX.value,
                target_layers=frozenset({CollisionLayer.PLAYER_HURTBOX.value}),
            )
        )

        # AI facing direction (toward target).
        self._facing: tuple[float, float] = (0.0, 1.0)

        # State.
        self._alive = True

    # -- Properties --

    @property
    def health(self) -> float:
        return self._health

    @health.setter
    def health(self, value: float) -> None:
        """Set health, updating alive state when it reaches 0."""
        self._health = max(0.0, value)
        if self._health <= 0.0:
            self._alive = False

    @property
    def alive(self) -> bool:
        return self._alive

    @property
    def invulnerable(self) -> bool:
        return self.invuln_service.invulnerable

    @property
    def facing(self) -> tuple[float, float]:
        """Unit vector facing toward the current target."""
        return self._facing

    @property
    def hitbox_aabb(self):
        """Active attack hitbox (None if not in active phase)."""
        if not self.attack_executor.hitbox_active():
            return None
        return self.attack_executor.hitbox_for(
            self.body.x,
            self.body.y,
            facing_x=self._facing[0],
            facing_y=self._facing[1],
        )

    # -- Per-frame update --

    def update(self, dt: float) -> None:
        """Advance combat timers: invulnerability, status, attack."""
        if not self._alive:
            return
        self.invuln_service.update(dt)
        self.status_manager.update(dt)
        self.attack_executor.update(dt)

    def integrate(self, dt: float) -> None:
        """Apply velocity to position (called after AI sets velocity)."""
        if not self._alive:
            return
        self.body.x += self.body.vx * dt
        self.body.y += self.body.vy * dt

    # -- Combat --

    def take_damage(self, amount: float) -> bool:
        """Apply damage, return True if killed."""
        if not self._alive:
            return False
        before = self._health
        self.health = self._health - amount  # uses property setter
        return before > 0.0 and self._health <= 0.0

    def set_facing(self, target_x: float, target_y: float) -> None:
        """Point facing vector toward a world position."""
        dx = target_x - self.body.x
        dy = target_y - self.body.y
        length = math.hypot(dx, dy)
        if length > 0.0:
            self._facing = (dx / length, dy / length)

    # -- DamageTarget protocol (for DamagePipeline) --

    @property
    def max_health(self) -> float:
        return self.config.max_health

    # -- Lifecycle --

    def reset(self) -> None:
        """Restore to full health (new spawn / room reset)."""
        self._health = self.config.max_health
        self._alive = True
        self.invuln_service.clear()
        self.status_manager.clear()
        self.attack_executor.cancel()
        self._facing = (0.0, 1.0)
        self.body.vx = 0.0
        self.body.vy = 0.0
