"""Ability/passive probe: do Q/E/R/T abilities and passives actually work?

Checks the full chain YAML → executor → runtime effect for:
  - Charge (Q): dash damage
  - Whirlwind (R): AoE damage
  - War Cry (T): toggle damage buff
  - Hardy passive: +25 max HP
  - Fury conditional: +15% dmg below 50% HP
  - Boon real effect on a landed hit (formula path)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.content_registry import ContentRegistry  # noqa: E402
from core.data_loader import load_category  # noqa: E402
from gameplay.enemies.enemy_factory import build_enemy  # noqa: E402
from gameplay.player.player import Player  # noqa: E402
from gameplay.player.player_stats import PlayerStats  # noqa: E402
from gameplay.playtest_scene import PlaytestScene  # noqa: E402
from input.input_manager import Action, ActionFrame  # noqa: E402
from rendering.camera import Camera  # noqa: E402
from world.room import Room  # noqa: E402

DT = 1.0 / 60.0
VIEWPORT = (1280, 720)
EMPTY = frozenset()


def build_registry() -> ContentRegistry:
    registry = ContentRegistry()
    for cat in ("player", "classes", "combat", "weapons", "abilities",
                "passives", "boons", "items", "enemies", "loot", "world"):
        registry.register_all(load_category(cat))
    return registry


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


def _spawn(scene: PlaytestScene, hp: int = 99999, dist: float = 40.0):
    px, py = scene.player.body.x, scene.player.body.y
    enemy, ai = build_enemy(scene._registry, "greybox_dummy", x=px + dist, y=py)
    enemy.health = hp
    scene._enemies = [(enemy, ai)]
    scene._encounter = scene._encounter.__class__()
    scene._encounter.activate(1)
    return enemy


def ability_probe(registry: ContentRegistry, slot: str, action: Action) -> dict:
    """Fire ONE ability at an adjacent target; measure damage."""
    scene = _scene(registry)
    scene._apply_class_loadout("warrior")
    scene._run.build.weapon_id = "warrior_sword"
    scene._reapply_weapon()
    enemy = _spawn(scene)
    start_hp = enemy.health

    # Face the enemy.
    scene.player.set_aim(1.0, 0.0)
    # Activate the ability through the player's executor.
    executor = scene.player.ability_executors.get(slot)
    if executor is None:
        return {"slot": slot, "error": "executor missing"}
    executor.activate()
    scene.update(ActionFrame(pressed=frozenset({action}), aim_x=1.0), DT)
    for _ in range(90):
        scene.update(ActionFrame(pressed=EMPTY, aim_x=1.0), DT)

    dealt = start_hp - enemy.health
    return {
        "slot": slot,
        "ability": executor.data.id,
        "type": executor.data.ability_type,
        "declared_effects": [e.get("type") for e in executor.data.effects],
        "dealt": round(dealt, 1),
    }


def passive_probe(registry: ContentRegistry) -> dict:
    """Does the Hardy passive (+25 HP) actually raise max HP?"""
    scene = _scene(registry)
    base_max = scene.player.stats.max_health
    scene._apply_class_loadout("warrior")  # applies hardy passive
    return {
        "base_max_hp": base_max,
        "after_loadout_max_hp": scene.player.stats.max_health,
        "build_max_health_bonus": scene._run.build.max_health_bonus,
    }


def fury_probe(registry: ContentRegistry) -> dict:
    """Fury conditional: +15% dmg when below 50% HP — does it apply?"""
    scene = _scene(registry)
    scene._apply_class_loadout("warrior")
    scene._run.build.weapon_id = "warrior_sword"
    scene._reapply_weapon()
    scene._run.build.register_conditional({
        "condition": "hp_below_50", "value": 0.15, "stat": "damage", "_active": False,
    })
    # Full HP: no fury.
    scene._run.build.update_conditionals(100.0, 100.0)
    mult_full = scene._run.build.damage_mult
    # Low HP: fury active.
    scene._run.build.update_conditionals(40.0, 100.0)
    mult_low = scene._run.build.damage_mult
    return {
        "damage_mult_full_hp": mult_full,
        "damage_mult_low_hp": mult_low,
        "fury_active": scene._run.build._fury_active,
    }


def boon_hit_probe(registry: ContentRegistry) -> dict:
    """Real damage of one landed hit with and without boon_damage_up."""
    def one_hit(with_boon: bool) -> float:
        scene = _scene(registry)
        scene._apply_class_loadout("warrior")
        scene._run.build.weapon_id = "warrior_sword"
        scene._reapply_weapon()
        if with_boon:
            from gameplay.builds.boon import BoonData, apply_boon_to_build
            doc = scene._registry.get("boons", "boon_damage_up")
            boon = BoonData.from_document(doc)
            apply_boon_to_build(boon, scene._run.build)
            scene._reapply_weapon()
            scene._apply_build_to_player()
        enemy = _spawn(scene)
        start_hp = enemy.health
        scene.update(ActionFrame(pressed=frozenset({Action.PRIMARY_ATTACK}), aim_x=1.0), DT)
        for _ in range(60):
            scene.update(ActionFrame(pressed=EMPTY, aim_x=1.0), DT)
        return start_hp - enemy.health

    return {"no_boon_dealt": round(one_hit(False), 1), "with_boon_dealt": round(one_hit(True), 1)}


if __name__ == "__main__":
    registry = build_registry()
    print("=== ABILITIES (warrior loadout) ===")
    for slot, action in [
        ("skill_q", Action.SKILL_1),
        ("skill_e", Action.SKILL_2),
        ("skill_r", Action.ULTIMATE),
        ("aura", Action.AURA),
    ]:
        print(" ", ability_probe(registry, slot, action))
    print("=== PASSIVE: hardy ===")
    print(" ", passive_probe(registry))
    print("=== CONDITIONAL: fury ===")
    print(" ", fury_probe(registry))
    print("=== BOON REAL HIT (boon_damage_up) ===")
    print(" ", boon_hit_probe(registry))
