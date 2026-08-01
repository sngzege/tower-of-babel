"""Isolated multi-hit probe: how many times does ONE attack hit one target?

CombatSystem adds hit_invuln (0.05s) after each dealt hit. If an attack's
active window is long (dummy: 0.3s = 18 frames), the same attack can land
multiple times. This probe measures the real per-attack hit count.
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
ATTACK = frozenset({Action.PRIMARY_ATTACK})
EMPTY = frozenset()


def build_registry() -> ContentRegistry:
    registry = ContentRegistry()
    for cat in ("player", "classes", "combat", "weapons", "abilities",
                "passives", "boons", "items", "enemies", "loot", "world"):
        registry.register_all(load_category(cat))
    return registry


def probe_attack_hits(registry: ContentRegistry, weapon_id: str) -> dict:
    """Fire ONE attack at an adjacent target; count hits + damage dealt."""
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
    scene._apply_weapon_to_player(weapon_id)
    scene._run.start()
    scene._run.build.weapon_id = weapon_id
    scene._reapply_weapon()

    # Adjacent target, invulnerable to AI movement (no AI update).
    px, py = player.body.x, player.body.y
    enemy, _ai = build_enemy(registry, "greybox_dummy", x=px + 40, y=py)
    enemy.health = 99999
    scene._enemies = [(enemy, _ai)]
    scene._encounter = scene._encounter.__class__()
    scene._encounter.activate(1)

    start_hp = enemy.health
    # Press attack ONCE, then idle frames while the attack resolves.
    scene.update(ActionFrame(pressed=ATTACK, aim_x=1.0, aim_y=0.0), DT)
    for _ in range(60):
        scene.update(ActionFrame(pressed=EMPTY, aim_x=1.0, aim_y=0.0), DT)

    dealt = start_hp - enemy.health
    exec_ = player.attack_executor
    return {
        "weapon": weapon_id,
        "declared_damage": exec_.data.damage,
        "total_dealt": dealt,
        "effective_hits": round(dealt / exec_.data.damage, 1),
        "attack_active_s": exec_.data.active,
        "attack_cooldown_s": exec_.data.cooldown,
    }


def probe_enemy_attack_hits(registry: ContentRegistry) -> dict:
    """How many times does ONE enemy attack hit the player?"""
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

    # Enemy adjacent; no player movement/attack; tick enemy AI so it attacks.
    px, py = player.body.x, player.body.y
    enemy, ai = build_enemy(registry, "greybox_dummy", x=px + 40, y=py)
    scene._enemies = [(enemy, ai)]
    scene._encounter = scene._encounter.__class__()
    scene._encounter.activate(1)

    start_hp = player.health
    # Run until the enemy completes exactly one attack cycle (windup+active+recovery)
    # then keep going a bit; count total HP lost while attack_executor is in active.
    for _ in range(120):  # 2s window
        scene.update(ActionFrame(pressed=EMPTY), DT)
    lost = start_hp - player.health
    return {
        "enemy_declared_damage": enemy.attack_executor.data.damage,
        "player_hp_lost": round(lost, 1),
        "effective_hits": round(lost / enemy.attack_executor.data.damage, 1),
        "enemy_active_s": enemy.attack_executor.data.active,
        "enemy_cooldown_s": enemy.attack_executor.data.cooldown,
    }


if __name__ == "__main__":
    registry = build_registry()
    print("=== ONE PLAYER ATTACK -> HOW MANY HITS? ===")
    for wid in ("warrior_sword", "warrior_spear", "warrior_axe"):
        print(" ", probe_attack_hits(registry, wid))
    print("=== ONE ENEMY ATTACK CYCLE -> HOW MANY HITS ON PLAYER? ===")
    print(" ", probe_enemy_attack_hits(registry))
