"""Boss AI: phase-based boss behaviour with distinct attack patterns.

Two phases:
  Phase 1 (100%-50% HP): Slow charge + sweep attack.
  Phase 2 (50%-0% HP): Faster movement + faster attacks + AoE shockwave.

The boss uses the same Enemy foundation as common enemies but with
boss-specific AI logic and multiple AttackExecutors (one per pattern).
"""

from __future__ import annotations

import math
from enum import Enum

from gameplay.combat.attack import AttackData, AttackExecutor
from gameplay.enemies.enemy import Enemy
from physics.collision import AABB


class BossPhase(Enum):
    PHASE_1 = "phase_1"
    PHASE_2 = "phase_2"
    DEAD = "dead"


class BossAI:
    """Phase-based boss AI with two attack patterns.

    The boss has TWO AttackExecutors:
      - primary_attack: charge/sweep (used in both phases, faster in P2)
      - aoe_attack: shockwave (only available in Phase 2, longer cooldown)

    Phase transitions happen at 50% HP.
    """

    def __init__(
        self,
        enemy: Enemy,
        primary_attack_data: AttackData,
        aoe_attack_data: AttackData | None = None,
    ) -> None:
        self.enemy = enemy
        self.phase: BossPhase = BossPhase.PHASE_1

        # Build two separate attack executors.
        self.primary = AttackExecutor(primary_attack_data)
        self.aoe = AttackExecutor(aoe_attack_data) if aoe_attack_data else None

        # Phase 1 tuning.
        self._p1_speed = enemy.config.speed

        # Phase 2 tuning — default boost.
        self._p2_speed = enemy.config.speed * 1.4

        # AOE cooldown tracker.
        self._aoe_cooldown_timer: float = 0.0
        self._aoe_cooldown: float = 4.0

        # Movement: oscillate between approach and circle.
        self._circle_timer: float = 0.0
        self._circle_dir: float = 1.0  # 1 or -1 for strafe direction

    @property
    def alive(self) -> bool:
        return self.phase is not BossPhase.DEAD and self.enemy.alive

    def _check_phase_transition(self) -> None:
        """Transition to Phase 2 when HP drops below 50%."""
        if self.phase is BossPhase.PHASE_1 and not self.enemy.alive:
            self.phase = BossPhase.DEAD
            return
        if (
            self.phase is BossPhase.PHASE_1
            and self.enemy.health <= self.enemy.config.max_health * 0.5
        ):
            self.phase = BossPhase.PHASE_2
            self.enemy.config.speed = self._p2_speed

    def _get_speed(self) -> float:
        if self.phase is BossPhase.PHASE_2:
            return self._p2_speed
        return self._p1_speed

    def update(
        self,
        player_x: float,
        player_y: float,
        dt: float,
    ) -> None:
        """Advance boss AI one frame.

        Sets velocity on the enemy's body. Caller must call
        enemy.integrate() afterward.
        """
        if not self.enemy.alive:
            self.phase = BossPhase.DEAD
            self.enemy.body.vx = 0.0
            self.enemy.body.vy = 0.0
            return

        self._check_phase_transition()
        self.enemy.set_facing(player_x, player_y)

        dx = player_x - self.enemy.body.x
        dy = player_y - self.enemy.body.y
        dist = math.hypot(dx, dy)

        if dist > 0.001:
            ndx = dx / dist
            ndy = dy / dist
        else:
            ndx, ndy = 0.0, 0.0

        speed = self._get_speed()

        # Update attack executors.
        self.primary.update(dt)
        if self.aoe:
            self.aoe.update(dt)
            self._aoe_cooldown_timer = max(0.0, self._aoe_cooldown_timer - dt)

        # Attack decision.
        primary_ready = self.primary.can_trigger()
        aoe_ready = (
            self.aoe is not None
            and self.aoe.can_trigger()
            and self._aoe_cooldown_timer <= 0.0
            and self.phase is BossPhase.PHASE_2
        )

        in_attack_range = dist <= 70.0
        if aoe_ready and in_attack_range:
            # Fire AoE shockwave.
            assert self.aoe is not None  # aoe_ready implies this
            self.aoe.trigger()
            self._aoe_cooldown_timer = self._aoe_cooldown
            self.enemy.body.vx = 0.0
            self.enemy.body.vy = 0.0
            return

        if primary_ready and in_attack_range:
            self.primary.trigger()
            self.enemy.body.vx = 0.0
            self.enemy.body.vy = 0.0
            return

        # Movement.
        if dist > 70.0:
            self.enemy.body.vx = ndx * speed
            self.enemy.body.vy = ndy * speed
        elif dist < 30.0:
            self.enemy.body.vx = -ndx * speed * 0.5
            self.enemy.body.vy = -ndy * speed * 0.5
        else:
            self._circle_timer += dt
            if self._circle_timer > 2.0:
                self._circle_dir *= -1.0
                self._circle_timer = 0.0

            perp_x = -ndy * self._circle_dir
            perp_y = ndx * self._circle_dir
            self.enemy.body.vx = perp_x * speed * 0.6
            self.enemy.body.vy = perp_y * speed * 0.6

    def get_hitbox_aabb(self) -> AABB | None:
        """Get the active hitbox AABB from whichever attack is active."""
        active = self.current_attack_hitbox()
        if active is None:
            return None
        executor, ox, oy = active
        fx, fy = self.enemy.facing
        return executor.hitbox_for(
            ox, oy,
            facing_x=fx,
            facing_y=fy,
        )

    def current_attack_hitbox(
        self,
    ) -> tuple[AttackExecutor, float, float] | None:
        """Return currently active attack executor + owner position.

        Returns:
            (active_executor, owner_x, owner_y) or None if no attack active.
        """
        if self.primary.hitbox_active():
            return (self.primary, self.enemy.body.x, self.enemy.body.y)
        if self.aoe is not None and self.aoe.hitbox_active():
            return (self.aoe, self.enemy.body.x, self.enemy.body.y)
        return None
