"""Enemy AI: simple state-based behaviours for greybox enemies.

Phase 5 greybox AI:
  IDLE → CHASE → ATTACK → CHASE (loop)
  Any → DEAD

This is a TECHNICAL framework, not a production AI system.
Production behaviours (Phase 5+) extend from here with custom behaviour
modules per enemy type.
"""

from __future__ import annotations

import math
from enum import Enum

from gameplay.enemies.enemy import Enemy


class AIState(Enum):
    """Top-level AI states for greybox enemies."""

    IDLE = "idle"
    CHASE = "chase"
    ATTACK = "attack"
    DEAD = "dead"


class SimpleAI:
    """Simple chase-and-attack AI for greybox enemies.

    Each frame:
      1. Face toward the player.
      2. If close enough, trigger an attack.
      3. If too far, chase.
      4. If dead, stop.

    The enemy's movement velocity is set each frame; the caller applies
    it via enemy.integrate() after calling this update.
    """

    def __init__(self, enemy: Enemy) -> None:
        self.enemy = enemy
        self._state: AIState = AIState.IDLE

    @property
    def state(self) -> AIState:
        return self._state

    def update(
        self,
        player_x: float,
        player_y: float,
        dt: float,
    ) -> None:
        """Advance AI one frame.

        Sets velocity on the enemy's body based on current AI state.
        The caller must call enemy.integrate() afterward to apply velocity.
        """
        if not self.enemy.alive:
            self._state = AIState.DEAD
            self.enemy.body.vx = 0.0
            self.enemy.body.vy = 0.0
            return

        # Always face the player.
        self.enemy.set_facing(player_x, player_y)

        dx = player_x - self.enemy.body.x
        dy = player_y - self.enemy.body.y
        dist = math.hypot(dx, dy)

        # If player is outside aggro range → idle.
        if dist > self.enemy.config.aggro_range:
            self._state = AIState.IDLE
            self.enemy.body.vx = 0.0
            self.enemy.body.vy = 0.0
            return

        # Check if attack is ready.
        attack_ready = self.enemy.attack_executor.can_trigger()
        # Cap the engage distance by the hitbox reach so the attack can
        # actually land (ideal_range may exceed reach — whiffing attacks
        # made enemies harmless; audit fix 2026-08-01).
        max_engage = min(
            self.enemy.config.attack_ideal_range,
            self.enemy.config.attack_hitbox_reach,
        )
        in_attack_range = dist <= max_engage

        if attack_ready and in_attack_range:
            # Start attacking.
            self.enemy.attack_executor.trigger()
            self._state = AIState.ATTACK
            self.enemy.body.vx = 0.0
            self.enemy.body.vy = 0.0
            return

        if self._state is AIState.ATTACK:
            # Mid-attack: don't move; the attack executor is advanced by
            # Enemy.update() (the scene calls both). Advancing it here too
            # would run the attack lifecycle at 2x speed (audit fix
            # 2026-08-01).
            self.enemy.body.vx = 0.0
            self.enemy.body.vy = 0.0
            # Attack finished → resume chasing.
            if self.enemy.attack_executor.can_trigger():
                self._state = AIState.CHASE
            return

        # Chase the player.
        self._state = AIState.CHASE
        if dist > 0.0:
            dir_x = dx / dist
            dir_y = dy / dist
            self.enemy.body.vx = dir_x * self.enemy.config.speed
            self.enemy.body.vy = dir_y * self.enemy.config.speed
        else:
            self.enemy.body.vx = 0.0
            self.enemy.body.vy = 0.0

    def reset(self) -> None:
        """Reset AI to idle."""
        self._state = AIState.IDLE
        self.enemy.body.vx = 0.0
        self.enemy.body.vy = 0.0
