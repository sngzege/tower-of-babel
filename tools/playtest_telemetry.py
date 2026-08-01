"""Playtest telemetry: measure the real game feel headlessly.

Drives the actual PlaytestScene (real data, real combat pipeline) and
reports the numbers that decide whether the game is FUN:

  - Player DPS with each weapon
  - Time-to-kill (TTK) for dummy / elite / boss
  - Player survivability vs enemy DPS
  - Build impact (do boons actually change damage?)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

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
CATEGORIES = (
    "player", "classes", "combat", "weapons", "abilities", "passives",
    "boons", "items", "enemies", "loot", "world", "village", "npcs",
    "progression", "unlocks",
)
ATTACK = frozenset({Action.PRIMARY_ATTACK})
EMPTY = frozenset()


def build_registry() -> ContentRegistry:
    registry = ContentRegistry()
    for cat in CATEGORIES:
        registry.register_all(load_category(cat))
    return registry


def build_arena_scene(registry: ContentRegistry, room_id: str) -> PlaytestScene:
    room = Room.from_document(registry.get("world", room_id))
    world = room.build_collision_world()
    player = Player(
        stats=PlayerStats.from_document(registry.get("player", "player_base")),
        x=room.player_spawn[0], y=room.player_spawn[1],
    )
    camera = Camera(VIEWPORT, zoom=2.0, follow_stiffness=8.0, bounds=room.bounds)
    scene = PlaytestScene(
        player=player, room=room, world=world, camera=camera,
        registry=registry, stage_manager=None, enemies=[],
    )
    scene.enter()
    return scene


def _reset_encounter(scene: PlaytestScene, total: int) -> None:
    scene._encounter = scene._encounter.__class__()
    scene._encounter.activate(total)
    scene._run.start()


def _spawn_right_of_player(scene: PlaytestScene, enemy_id: str, dist: float = 50.0):
    """Spawn an enemy just right of the player so aim_x=1.0 hits it."""
    px, py = scene.player.body.x, scene.player.body.y
    return build_enemy(scene._registry, enemy_id, x=px + dist, y=py)


def weapon_dps(scene: PlaytestScene, weapon_id: str, seconds: float = 10.0) -> dict:
    """Measure sustained DPS by reading enemy health (damage numbers expire)."""
    scene._apply_weapon_to_player(weapon_id)
    enemy, _ai = _spawn_right_of_player(scene, "greybox_elite")
    enemy.health = 999999  # never dies during measurement
    scene._enemies = [(enemy, _ai)]
    _reset_encounter(scene, 1)
    scene._run.build.weapon_id = weapon_id
    scene._reapply_weapon()

    frames = int(seconds / DT)
    start_hp = enemy.health
    for _ in range(frames):
        scene.update(ActionFrame(pressed=ATTACK, aim_x=1.0, aim_y=0.0), DT)
    dealt = start_hp - enemy.health
    return {"weapon": weapon_id, "dps": round(dealt / seconds, 1), "total": round(dealt, 1)}


def ttk_enemy(scene: PlaytestScene, weapon_id: str, enemy_id: str) -> float:
    """Time (s) to kill one enemy with basic attacks only."""
    scene._apply_weapon_to_player(weapon_id)
    enemy, _ai = _spawn_right_of_player(scene, enemy_id)
    scene._enemies = [(enemy, _ai)]
    _reset_encounter(scene, 1)
    scene._run.build.weapon_id = weapon_id
    scene._reapply_weapon()

    steps = 0
    while enemy.alive and steps < 1800:
        scene.update(ActionFrame(pressed=ATTACK, aim_x=1.0, aim_y=0.0), DT)
        steps += 1
    return round(steps * DT, 2) if not enemy.alive else -1.0


def ttk_boss(scene: PlaytestScene, weapon_id: str) -> float:
    """Time (s) to kill the boss with basic attacks only."""
    scene._apply_weapon_to_player(weapon_id)
    px, py = scene.player.body.x, scene.player.body.y
    primary = AttackData.from_document(
        scene._registry.get("combat", "boss_primary_attack")
    )
    aoe = AttackData.from_document(scene._registry.get("combat", "boss_aoe_attack"))
    boss, boss_ai = build_boss(
        scene._registry, "first_boss", x=px + 60, y=py,
        primary_attack=primary, aoe_attack=aoe,
    )
    scene._boss = boss
    scene._boss_ai = boss_ai
    _reset_encounter(scene, 1)
    scene._run.build.weapon_id = weapon_id
    scene._reapply_weapon()

    steps = 0
    while boss.alive and steps < 3600:
        # Keep the player alive so they can keep attacking (boss multi-hit
        # would otherwise kill a static 100 HP player).
        scene.player.health = scene.player.stats.max_health
        scene.update(ActionFrame(pressed=ATTACK, aim_x=1.0, aim_y=0.0), DT)
        steps += 1
    return round(steps * DT, 2) if not boss.alive else -1.0


def player_survivability(
    scene: PlaytestScene, enemy_id: str, count: int
) -> dict:
    """How long the player survives vs N enemies (no dodging, no attacking)."""
    px, py = scene.player.body.x, scene.player.body.y
    enemies = []
    for i in range(count):
        e, ai = build_enemy(
            scene._registry, enemy_id, x=px + 40 + i * 40, y=py - 30 + (i % 2) * 60
        )
        enemies.append((e, ai))
    scene._enemies = enemies
    _reset_encounter(scene, count)

    steps = 0
    hits_taken = 0
    last_hp = scene.player.health
    while scene.player.alive and steps < 3600:
        scene.update(ActionFrame(), DT)
        if scene.player.health < last_hp:
            hits_taken += 1
            last_hp = scene.player.health
        steps += 1
    return {
        "enemy": enemy_id, "count": count,
        "survived_s": round(steps * DT, 1),
        "damage_events": hits_taken,
        "player_hp_at_end": round(scene.player.health, 1),
    }


def boon_impact(scene: PlaytestScene) -> dict:
    """Do boons change real damage? Measure before/after."""
    scene._apply_weapon_to_player("warrior_sword")
    scene._run.start()
    scene._run.build.weapon_id = "warrior_sword"
    scene._reapply_weapon()
    base = scene.player.attack_executor.data.damage

    from gameplay.builds.boon import BoonData, apply_boon_to_build

    doc = scene._registry.get("boons", "boon_damage_up")
    boon = BoonData.from_document(doc)
    apply_boon_to_build(boon, scene._run.build)
    scene._reapply_weapon()
    scene._apply_build_to_player()
    after = scene.player.attack_executor.data.damage

    return {
        "boon": boon.id, "name": boon.name,
        "base_damage": base, "after_damage": after,
        "build_damage_mult": scene._run.build.damage_mult,
    }


if __name__ == "__main__":
    registry = build_registry()

    print("=== WEAPON DPS (10s sustained, vs immortal elite) ===")
    for wid in ("warrior_sword", "warrior_spear", "warrior_axe"):
        s = build_arena_scene(registry, "greybox_combat_hall")
        print(" ", weapon_dps(s, wid))

    print("=== TTK (basic attacks only) ===")
    for wid in ("warrior_sword", "warrior_spear", "warrior_axe"):
        s = build_arena_scene(registry, "greybox_combat_hall")
        print(f"  dummy  vs {wid}: {ttk_enemy(s, wid, 'greybox_dummy')}s")
        s = build_arena_scene(registry, "greybox_combat_hall")
        print(f"  elite  vs {wid}: {ttk_enemy(s, wid, 'greybox_elite')}s")
        s = build_arena_scene(registry, "greybox_combat_hall")
        print(f"  boss   vs {wid}: {ttk_boss(s, wid)}s")

    print("=== PLAYER SURVIVABILITY (no action) ===")
    for n in (1, 2, 3):
        s = build_arena_scene(registry, "greybox_combat_hall")
        print(" ", player_survivability(s, "greybox_dummy", n))

    print("=== BOON IMPACT (boon_damage_up) ===")
    s = build_arena_scene(registry, "greybox_combat_hall")
    print(" ", boon_impact(s))
