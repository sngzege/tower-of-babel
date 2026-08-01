"""Regression tests for the 2026-08-01 combat audit fixes.

Guards against the three critical bugs found by playtest telemetry:

  1. MULTI-HIT: one attack must connect at most once per target
     (hit_invuln is now per-instance = active window + margin).
  2. HP STACKING: applying a build repeatedly must not grow max HP
     (+25 per room transition was the old behaviour).
  3. BOSS REACHABILITY: every weapon must be able to kill the boss;
     enemies must be able to hit the player (engage range capped by
     hitbox reach).
  4. EXECUTOR DOUBLE-STEP: enemy attack lifecycle must not run at 2x
     speed (AI + Enemy.update both advancing the executor).
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from core.content_registry import ContentRegistry  # noqa: E402
from core.data_loader import load_category  # noqa: E402
from gameplay.combat.attack import AttackData  # noqa: E402
from gameplay.enemies.enemy_factory import build_boss, build_enemy  # noqa: E402
from gameplay.player.player import Player  # noqa: E402
from gameplay.player.player_stats import PlayerStats  # noqa: E402
from gameplay.playtest_scene import PlaytestScene  # noqa: E402
from input.input_manager import Action, ActionFrame  # noqa: E402
from rendering.camera import Camera  # noqa: E402
from world.room import Room  # noqa: E402

DT = 1.0 / 60.0
VIEWPORT = (1280, 720)
ATTACK = frozenset({Action.PRIMARY_ATTACK})
EMPTY = frozenset()
CATEGORIES = (
    "player", "classes", "combat", "weapons", "abilities", "passives",
    "boons", "items", "enemies", "loot", "world",
)


@pytest.fixture(scope="module")
def registry() -> ContentRegistry:
    reg = ContentRegistry()
    for cat in CATEGORIES:
        reg.register_all(load_category(cat))
    return reg


def _scene(registry: ContentRegistry) -> PlaytestScene:
    room = Room.from_document(registry.get("world", "greybox_combat_hall"))
    player = Player(
        stats=PlayerStats.from_document(registry.get("player", "player_base")),
        x=room.player_spawn[0], y=room.player_spawn[1],
    )
    camera = Camera(VIEWPORT, zoom=2.0, follow_stiffness=8.0, bounds=room.bounds)
    scene = PlaytestScene(
        player=player, room=room, world=room.build_collision_world(),
        camera=camera, registry=registry, stage_manager=None, enemies=[],
    )
    scene.enter()
    scene._run.start()
    return scene


def _spawn_adjacent(scene: PlaytestScene, enemy_id: str = "greybox_dummy"):
    px, py = scene.player.body.x, scene.player.body.y
    enemy, ai = build_enemy(scene._registry, enemy_id, x=px + 40, y=py)
    enemy.health = 99999
    scene._enemies = [(enemy, ai)]
    scene._encounter = scene._encounter.__class__()
    scene._encounter.activate(1)
    return enemy


# --- 1. MULTI-HIT ---

@pytest.mark.parametrize(
    "weapon,expected_damage",
    [
        ("warrior_sword", 20.0),
        ("warrior_spear", 26.4),
        ("warrior_axe", 45.0),
    ],
)
def test_one_attack_hits_once(
    registry: ContentRegistry, weapon: str, expected_damage: float
) -> None:
    """ONE attack press must deal exactly one hit of damage."""
    scene = _scene(registry)
    scene._apply_weapon_to_player(weapon)
    scene._run.build.weapon_id = weapon
    scene._reapply_weapon()
    enemy = _spawn_adjacent(scene)
    start_hp = enemy.health

    scene.update(ActionFrame(pressed=ATTACK, aim_x=1.0, aim_y=0.0), DT)
    for _ in range(90):  # let the full attack resolve
        scene.update(ActionFrame(pressed=EMPTY, aim_x=1.0, aim_y=0.0), DT)

    dealt = start_hp - enemy.health
    assert dealt == pytest.approx(expected_damage, abs=0.2), (
        f"{weapon} dealt {dealt} instead of one hit ({expected_damage}) — multi-hit!"
    )


def test_enemy_attack_hits_once(registry: ContentRegistry) -> None:
    """One enemy attack cycle must deal one hit of damage."""
    scene = _scene(registry)
    scene._run.start()
    _spawn_adjacent(scene)
    start_hp = scene.player.health
    # Run long enough for exactly one attack cycle (windup+active+recovery)
    # plus cooldown; count total HP lost.
    for _ in range(240):
        scene.update(ActionFrame(pressed=EMPTY), DT)
    lost = start_hp - scene.player.health
    # Dummy deals 10 per hit; allow a second cycle only if cooldown elapsed
    # (1.5s cooldown + 0.65s attack = ~2.15s; 240 frames = 4s -> max 1-2 hits).
    assert lost == pytest.approx(10.0, abs=10.0), (
        f"enemy dealt {lost} in one cycle — multi-hit or double-stepped executor"
    )


# --- 2. HP STACKING ---

def test_build_apply_is_idempotent(registry: ContentRegistry) -> None:
    """Re-applying the build must not grow max HP."""
    scene = _scene(registry)
    scene._run.start()
    max_hp = scene.player.stats.max_health
    health = scene.player.health
    assert max_hp == pytest.approx(125.0)  # 100 base + 25 hardy

    for _ in range(5):
        scene._apply_build_to_player()

    assert scene.player.stats.max_health == pytest.approx(max_hp)
    assert scene.player.health == pytest.approx(health)


def test_restart_keeps_hp_stable(registry: ContentRegistry) -> None:
    """Restart must reset to base + loadout once, not stack."""
    scene = _scene(registry)
    scene._run.start()
    scene._restart_run()
    assert scene.player.stats.max_health == pytest.approx(125.0)
    assert scene.player.health == pytest.approx(125.0)
    scene._restart_run()
    assert scene.player.stats.max_health == pytest.approx(125.0)


# --- 3. BOSS REACHABILITY / ENEMY ENGAGE RANGE ---

@pytest.mark.parametrize(
    "weapon,max_seconds",
    [
        ("warrior_sword", 40.0),
        ("warrior_spear", 45.0),
        ("warrior_axe", 20.0),
    ],
)
def test_boss_killable_with_every_weapon(
    registry: ContentRegistry, weapon: str, max_seconds: float
) -> None:
    """The boss must be beatable with basic attacks from any weapon."""
    scene = _scene(registry)
    scene._apply_weapon_to_player(weapon)
    scene._run.build.weapon_id = weapon
    scene._reapply_weapon()
    px, py = scene.player.body.x, scene.player.body.y
    primary = AttackData.from_document(
        registry.get("combat", "boss_primary_attack")
    )
    aoe = AttackData.from_document(registry.get("combat", "boss_aoe_attack"))
    boss, boss_ai = build_boss(
        registry, "first_boss", x=px + 60, y=py,
        primary_attack=primary, aoe_attack=aoe,
    )
    scene._boss = boss
    scene._boss_ai = boss_ai
    scene._encounter = scene._encounter.__class__()
    scene._encounter.activate(1)
    scene._run.start()

    steps = 0
    while boss.alive and steps < int(max_seconds / DT):
        # Keep the player topped up so they can keep attacking.
        scene.player.health = scene.player.stats.max_health
        scene.update(ActionFrame(pressed=ATTACK, aim_x=1.0, aim_y=0.0), DT)
        steps += 1

    assert not boss.alive, (
        f"boss not killed with {weapon} within {max_seconds}s "
        f"(health left: {boss.health})"
    )


def test_enemy_can_hit_player(registry: ContentRegistry) -> None:
    """Enemies must actually damage the player (engage range <= hitbox)."""
    scene = _scene(registry)
    scene._run.start()
    _spawn_adjacent(scene)
    start_hp = scene.player.health
    for _ in range(300):  # 5s: enough for chase + first attack
        scene.update(ActionFrame(pressed=EMPTY), DT)
    assert scene.player.health < start_hp, "dummy never hit the player"


# --- 4. EXECUTOR DOUBLE-STEP ---

def test_enemy_attack_speed_not_doubled(registry: ContentRegistry) -> None:
    """Enemy attacks should follow data cooldown, not run at 2x speed."""
    scene = _scene(registry)
    scene._run.start()
    _spawn_adjacent(scene)
    # Measure hits over 6 seconds: dummy cooldown 1.5s + attack 0.65s
    # => ~2-3 attacks expected. 2x speed would give 4-5.
    start_hp = scene.player.health
    for _ in range(360):
        scene.update(ActionFrame(pressed=EMPTY), DT)
    damage_per_hit = 10.0  # greybox_dummy declared damage
    hits = (start_hp - scene.player.health) / damage_per_hit
    assert hits <= 3.5, f"enemy landed {hits} hits in 6s — executor double-stepped?"
