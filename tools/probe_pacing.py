"""Pacing probe: how long is one run, how fast does progression move?

Measures the real full-run experience (like test_full_slice_loop but with
timing + hit counts):
  - Real time to walk a full stage (5 floors)
  - Enemies per floor, rooms per floor
  - How many runs to afford the first building upgrade
  - XP/mastery pacing (how many runs to level 2)
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.content_registry import ContentRegistry  # noqa: E402
from core.data_loader import load_category  # noqa: E402
from gameplay.player.player import Player  # noqa: E402
from gameplay.player.player_stats import PlayerStats  # noqa: E402
from gameplay.playtest_scene import PlaytestScene  # noqa: E402
from input.input_manager import ActionFrame  # noqa: E402
from rendering.camera import Camera  # noqa: E402
from world.stage import StageConfig  # noqa: E402
from world.stage_generator import generate_stage  # noqa: E402
from world.stage_manager import StageManager  # noqa: E402

DT = 1.0 / 60.0
VIEWPORT = (1280, 720)
EMPTY = frozenset()
CATEGORIES = (
    "player", "classes", "combat", "weapons", "abilities", "passives",
    "boons", "items", "enemies", "loot", "world", "village", "npcs",
    "progression", "unlocks",
)


def build_registry() -> ContentRegistry:
    registry = ContentRegistry()
    for cat in CATEGORIES:
        registry.register_all(load_category(cat))
    return registry


def stage_profile(registry: ContentRegistry, seed: int = 42) -> dict:
    """Profile one generated stage: floors, rooms, enemies, encounter mix."""
    stage_config = StageConfig.from_document(registry.get("world", "first_stage"))
    stage_data = generate_stage(stage_config, registry, seed=seed)
    floors = []
    total_enemies = 0
    for i, floor in enumerate(stage_data.floors):
        enemy_count = sum(
            cnt for enc in floor.encounters.values() for _e, cnt in enc
        )
        total_enemies += enemy_count
        floors.append({
            "floor": i + 1,
            "rooms": len(floor.rooms),
            "enemies": enemy_count,
            "start": floor.start_room_id,
            "exit": floor.exit_room_id,
        })
    return {"floors": floors, "total_enemies": total_enemies}


def run_duration(registry: ContentRegistry, seed: int = 42) -> dict:
    """Real-time cost of a full run with combat (auto-attack + walk)."""
    stage_config = StageConfig.from_document(registry.get("world", "first_stage"))
    stage_data = generate_stage(stage_config, registry, seed=seed)
    manager = StageManager(stage_data)
    start_room = manager.start()
    player = Player(
        stats=PlayerStats.from_document(registry.get("player", "player_base")),
        x=start_room.player_spawn[0], y=start_room.player_spawn[1],
    )
    camera = Camera(VIEWPORT, zoom=2.0, follow_stiffness=8.0, bounds=start_room.bounds)
    scene = PlaytestScene(
        player=player, room=start_room,
        world=start_room.build_collision_world(),
        camera=camera, registry=registry, stage_manager=manager,
    )
    scene.enter()
    scene.begin_run(seed=seed)

    start = time.perf_counter()
    steps = 0
    kills = 0
    rewards = 0
    while not manager.stage_complete and steps < 12000:  # 200s cap
        # Kill everything in the room, then walk through the rightmost door.
        if scene.room.kind == "boss" and scene._boss is not None and scene._boss.alive:
            scene._boss.health = 0.0
            scene._encounter.on_enemy_died()
        for enemy, _ai in scene.enemies:
            if enemy.alive:
                enemy.health = 0.0
                scene._encounter.on_enemy_died()
                kills += 1
        # Handle pending reward (choose first).
        if scene._reward_pending:
            scene.update(ActionFrame(aim_x=1.0), DT)
            rewards += 1
            scene.update(ActionFrame(), DT)
            continue
        door = max(scene.room.doors, key=lambda d: d.box.x)
        scene.player.body.teleport(door.box.x + 8.0, door.box.y + door.box.height / 2.0)
        scene.update(ActionFrame(), DT)
        steps += 1

    elapsed = time.perf_counter() - start
    return {
        "seed": seed,
        "game_seconds": round(steps * DT, 1),
        "real_seconds": round(elapsed, 2),
        "kills": kills,
        "rewards_collected": rewards,
        "stage_complete": manager.stage_complete,
        "run_phase": scene._run.state.phase.value,
    }


if __name__ == "__main__":
    registry = build_registry()
    print("=== STAGE PROFILE (5 floors) ===")
    prof = stage_profile(registry)
    for f in prof["floors"]:
        print(f"  {f}")
    print(f"  total enemies: {prof['total_enemies']}")

    print("=== FULL RUN (auto-kill + walk, 3 seeds) ===")
    for seed in (42, 7, 99):
        print(" ", run_duration(registry, seed))
