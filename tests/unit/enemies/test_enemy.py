"""Tests for enemy entity, AI, and factory (Phase 5)."""

from __future__ import annotations

import pytest

from gameplay.combat.attack import AttackPhase
from gameplay.combat.combat_system import CombatEntity, CombatSystem
from gameplay.combat.damage import DamageInstance
from gameplay.enemies.enemy import Enemy, EnemyConfig
from gameplay.enemies.enemy_ai import AIState, SimpleAI
from gameplay.enemies.enemy_factory import build_enemy
from physics.collision import CollisionLayer

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dummy_config() -> EnemyConfig:
    return EnemyConfig(
        id="test_dummy",
        name="Test Dummy",
        max_health=50.0,
        damage=10.0,
        speed=60.0,
        body_width=24.0,
        body_height=24.0,
        attack_windup=0.05,
        attack_active=0.15,
        attack_recovery=0.1,
        attack_cooldown=0.5,
        attack_damage=10.0,
        attack_hitbox_spread=16.0,
        attack_hitbox_reach=20.0,
        attack_min_range=15.0,
        attack_ideal_range=25.0,
        aggro_range=200.0,
    )


@pytest.fixture
def dummy_enemy(dummy_config: EnemyConfig) -> Enemy:
    return Enemy(config=dummy_config, x=200.0, y=200.0)


# ---------------------------------------------------------------------------
# Enemy entity tests
# ---------------------------------------------------------------------------

class TestEnemyEntity:
    def test_spawns_alive(self, dummy_enemy: Enemy) -> None:
        assert dummy_enemy.alive
        assert dummy_enemy.health == 50.0

    def test_take_damage_reduces_health(self, dummy_enemy: Enemy) -> None:
        killed = dummy_enemy.take_damage(10.0)
        assert not killed
        assert dummy_enemy.health == 40.0
        assert dummy_enemy.alive

    def test_take_damage_kills_when_health_depleted(self, dummy_enemy: Enemy) -> None:
        killed = dummy_enemy.take_damage(50.0)
        assert killed
        assert dummy_enemy.health == 0.0
        assert not dummy_enemy.alive

    def test_overkill_handled(self, dummy_enemy: Enemy) -> None:
        killed = dummy_enemy.take_damage(100.0)
        assert killed
        assert dummy_enemy.health == 0.0
        assert not dummy_enemy.alive

    def test_dead_enemy_rejects_damage(self, dummy_enemy: Enemy) -> None:
        dummy_enemy.take_damage(100.0)
        assert not dummy_enemy.alive
        killed = dummy_enemy.take_damage(10.0)
        assert not killed  # already dead

    def test_reset_restores_health(self, dummy_enemy: Enemy) -> None:
        dummy_enemy.take_damage(30.0)
        assert dummy_enemy.health == 20.0
        dummy_enemy.reset()
        assert dummy_enemy.health == 50.0
        assert dummy_enemy.alive

    def test_attack_executor_starts_idle(self, dummy_enemy: Enemy) -> None:
        assert dummy_enemy.attack_executor.state.phase is AttackPhase.IDLE

    def test_attack_can_be_triggered(self, dummy_enemy: Enemy) -> None:
        assert dummy_enemy.attack_executor.trigger()
        assert dummy_enemy.attack_executor.state.phase is AttackPhase.WINDUP

    def test_attack_produces_hitbox_on_active(self, dummy_enemy: Enemy) -> None:
        dummy_enemy.set_facing(300.0, 200.0)  # face right
        dummy_enemy.attack_executor.trigger()
        # Advance past windup into active.
        dummy_enemy.attack_executor.update(0.06)
        assert dummy_enemy.attack_executor.hitbox_active()
        hitbox = dummy_enemy.hitbox_aabb
        assert hitbox is not None
        # Hitbox should be to the right of the enemy.
        assert hitbox.center[0] > dummy_enemy.body.x

    def test_no_hitbox_before_active(self, dummy_enemy: Enemy) -> None:
        assert dummy_enemy.hitbox_aabb is None

    def test_hurtbox_layer_is_enemy(self, dummy_enemy: Enemy) -> None:
        assert dummy_enemy.hurtbox.layer is CollisionLayer.ENEMY_HURTBOX

    def test_facing_updates_toward_point(self, dummy_enemy: Enemy) -> None:
        dummy_enemy.set_facing(300.0, 200.0)  # target is to the right
        fx, fy = dummy_enemy.facing
        assert fx > 0.0  # facing right
        assert abs(fy) < 0.001  # mostly horizontal

        dummy_enemy.set_facing(200.0, 100.0)  # target is above
        fx, fy = dummy_enemy.facing
        assert fy < 0.0  # facing up (y is inverted on screen)

    def test_update_advances_combat_timers(self, dummy_enemy: Enemy) -> None:
        dummy_enemy.attack_executor.trigger()
        dummy_enemy.attack_executor.update(0.06)  # past 0.05 windup
        assert dummy_enemy.attack_executor.state.phase is AttackPhase.ACTIVE
        dummy_enemy.update(0.2)
        # Attack should have advanced into recovery or beyond.
        assert dummy_enemy.attack_executor.state.phase is not AttackPhase.ACTIVE

    def test_integrate_moves_body(self, dummy_enemy: Enemy) -> None:
        start_x = dummy_enemy.body.x
        dummy_enemy.body.vx = 60.0  # 60 px/s
        dummy_enemy.integrate(1.0)
        assert dummy_enemy.body.x == start_x + 60.0


# ---------------------------------------------------------------------------
# Enemy AI tests
# ---------------------------------------------------------------------------

class TestSimpleAI:
    def test_starts_idle(self, dummy_enemy: Enemy) -> None:
        ai = SimpleAI(dummy_enemy)
        assert ai.state is AIState.IDLE

    def test_player_in_aggro_range_triggers_chase(self, dummy_enemy: Enemy) -> None:
        ai = SimpleAI(dummy_enemy)
        # Player at (300, 200) — 100 px away, within aggro range.
        ai.update(player_x=300.0, player_y=200.0, dt=0.016)
        assert ai.state is AIState.CHASE
        # Enemy should be moving right (positive vx).
        assert dummy_enemy.body.vx > 0.0

    def test_idle_when_player_out_of_range(self, dummy_enemy: Enemy) -> None:
        ai = SimpleAI(dummy_enemy)
        # Player at (500, 200) — 300 px away, outside aggro_range (200.0).
        ai.update(player_x=500.0, player_y=200.0, dt=0.016)
        assert ai.state is AIState.IDLE
        assert dummy_enemy.body.vx == 0.0

    def test_attacks_when_close(self, dummy_enemy: Enemy) -> None:
        ai = SimpleAI(dummy_enemy)
        # Player at (220, 200) — 20 px away, within ideal_range (25.0).
        ai.update(player_x=220.0, player_y=200.0, dt=0.016)
        assert ai.state is AIState.ATTACK
        assert not dummy_enemy.attack_executor.can_trigger()  # attack started

    def test_enemy_stops_moving_during_attack(self, dummy_enemy: Enemy) -> None:
        ai = SimpleAI(dummy_enemy)
        # Close enough to attack.
        ai.update(player_x=220.0, player_y=200.0, dt=0.016)
        assert ai.state is AIState.ATTACK
        assert dummy_enemy.body.vx == 0.0
        assert dummy_enemy.body.vy == 0.0

    def test_resumes_chase_after_attack(self, dummy_enemy: Enemy) -> None:
        ai = SimpleAI(dummy_enemy)
        # Trigger attack.
        ai.update(player_x=220.0, player_y=200.0, dt=0.016)
        assert ai.state is AIState.ATTACK
        # Run enough frames for attack to complete.
        for _ in range(120):  # 120 frames at dt=0.016 = ~2s
            ai.update(player_x=220.0, player_y=200.0, dt=0.016)
            if ai.state is AIState.CHASE:
                break
        assert ai.state is AIState.CHASE

    def test_dead_ai_does_nothing(self, dummy_enemy: Enemy) -> None:
        ai = SimpleAI(dummy_enemy)
        dummy_enemy._alive = False
        ai.update(player_x=220.0, player_y=200.0, dt=0.016)
        assert ai.state is AIState.DEAD
        assert dummy_enemy.body.vx == 0.0


# ---------------------------------------------------------------------------
# Enemy factory tests
# ---------------------------------------------------------------------------

class _FakeRegistry:
    """Minimal registry stub for factory tests."""

    def __init__(self, document: dict) -> None:
        self._doc = document

    def get(self, category: str, enemy_id: str) -> dict:
        return self._doc


class TestEnemyFactory:
    def test_build_enemy_from_data(self) -> None:
        doc = {
            "id": "greybox_dummy",
            "name": "Greybox Training Dummy",
            "stats": {"health": 50, "damage": 10, "speed": 60.0},
            "body": {"width": 24.0, "height": 24.0},
            "hurtbox": {"width": 22.0, "height": 22.0},
            "attack": {
                "windup": 0.2,
                "active": 0.3,
                "recovery": 0.15,
                "cooldown": 1.5,
                "damage": 10.0,
                "hitbox_spread": 18.0,
                "hitbox_reach": 20.0,
                "min_range": 20.0,
                "ideal_range": 28.0,
            },
            "aggro_range": 200.0,
        }
        registry = _FakeRegistry(doc)
        enemy, ai = build_enemy(registry, "greybox_dummy", x=100.0, y=100.0)
        assert enemy is not None
        assert ai is not None
        assert enemy.config.max_health == 50.0
        assert enemy.config.speed == 60.0
        assert enemy.body.x == 100.0
        assert enemy.body.y == 100.0
        assert isinstance(ai, SimpleAI)

    def test_factory_handles_optional_fields(self) -> None:
        """Minimal document should still build."""
        doc = {
            "id": "minimal_dummy",
            "name": "Minimal",
            "stats": {"health": 10, "damage": 5, "speed": 30.0},
        }
        registry = _FakeRegistry(doc)
        enemy, ai = build_enemy(registry, "minimal_dummy")
        assert enemy is not None
        assert enemy.config.max_health == 10.0
        assert enemy.config.speed == 30.0
        # Optional fields should have sensible defaults.
        assert enemy.config.body_width == 24.0
        assert enemy.config.attack_damage == 10.0  # default from AttackData


# ---------------------------------------------------------------------------
# Combat resolution tests (player attacks enemy)
# ---------------------------------------------------------------------------

class TestCombatResolution:
    def test_player_attack_hits_enemy(self, dummy_enemy: Enemy) -> None:
        combat = CombatSystem()
        # Create a hitbox that overlaps the enemy.
        hitbox = dummy_enemy.hurtbox.box_at(200.0, 200.0)
        hitbox = hitbox.moved(-5.0, -5.0)  # slightly offset but still overlapping

        damage = DamageInstance(value=25.0, types=frozenset({"physical"}))
        enemy_entity = CombatEntity(
            id="test_dummy",
            body_x=200.0,
            body_y=200.0,
            hurtbox_aabb=dummy_enemy.hurtbox.box_at(200.0, 200.0),
            vulnerable=True,
            damage_target=dummy_enemy,
        )

        hits = combat.resolve_hits(
            hitboxes=[("player", hitbox, damage)],
            entities=[enemy_entity],
        )

        assert len(hits) == 1
        assert not hits[0].result.invulnerable
        assert hits[0].result.dealt == 25.0
        assert dummy_enemy.health == 25.0  # 50 - 25

    def test_dead_enemy_not_hittable(self, dummy_enemy: Enemy) -> None:
        combat = CombatSystem()
        dummy_enemy.take_damage(100.0)  # kill

        hitbox = dummy_enemy.hurtbox.box_at(200.0, 200.0)

        enemy_entity = CombatEntity(
            id="test_dummy",
            body_x=200.0,
            body_y=200.0,
            hurtbox_aabb=dummy_enemy.hurtbox.box_at(200.0, 200.0),
            vulnerable=False,  # dead
            damage_target=dummy_enemy,
        )

        damage = DamageInstance(value=25.0, types=frozenset({"physical"}))
        hits = combat.resolve_hits(
            hitboxes=[("player", hitbox, damage)],
            entities=[enemy_entity],
        )

        assert len(hits) == 0  # no hit because vulnerable=False

    def test_invulnerable_enemy_blocks_damage(self, dummy_enemy: Enemy) -> None:
        from gameplay.combat.invulnerability import InvulnerabilityService

        combat = CombatSystem()
        invuln = InvulnerabilityService()
        invuln.add("test", 1.0)
        dummy_enemy.invuln_service = invuln

        hitbox = dummy_enemy.hurtbox.box_at(200.0, 200.0)
        enemy_entity = CombatEntity(
            id="test_dummy",
            body_x=200.0,
            body_y=200.0,
            hurtbox_aabb=dummy_enemy.hurtbox.box_at(200.0, 200.0),
            vulnerable=True,
            damage_target=dummy_enemy,
            invuln_service=invuln,
        )

        damage = DamageInstance(value=25.0, types=frozenset({"physical"}))
        hits = combat.resolve_hits(
            hitboxes=[("player", hitbox, damage)],
            entities=[enemy_entity],
        )

        assert len(hits) == 1
        assert hits[0].result.invulnerable
        assert hits[0].result.dealt == 0.0
        assert dummy_enemy.health == 50.0  # no damage taken

    def test_non_overlapping_hitbox_does_not_hit(self, dummy_enemy: Enemy) -> None:
        combat = CombatSystem()
        # Hitbox far away from enemy.
        hitbox = dummy_enemy.hurtbox.box_at(200.0, 200.0).moved(500.0, 500.0)

        enemy_entity = CombatEntity(
            id="test_dummy",
            body_x=200.0,
            body_y=200.0,
            hurtbox_aabb=dummy_enemy.hurtbox.box_at(200.0, 200.0),
            vulnerable=True,
            damage_target=dummy_enemy,
        )

        damage = DamageInstance(value=25.0, types=frozenset({"physical"}))
        hits = combat.resolve_hits(
            hitboxes=[("player", hitbox, damage)],
            entities=[enemy_entity],
        )

        assert len(hits) == 0
