"""Capture in-game combat + boss-fight screenshots (real stage, real boss).

Walks the stage to the boss floor, spawns the boss via the normal encounter
pipeline, lets the boss AI act, and captures:
  - 05_combat_room.png   : fighting greybox dummies in a combat room
  - 06_boss_fight.png    : boss room with the Warden (phase 1)
  - 07_boss_phase2.png   : boss at phase 2 (below 50% HP)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.content_registry import ContentRegistry  # noqa: E402
from core.data_loader import load_category  # noqa: E402
from engine.game import Game  # noqa: E402
from gameplay.player.player import Player  # noqa: E402
from gameplay.player.player_stats import PlayerStats  # noqa: E402
from gameplay.playtest_scene import PlaytestScene  # noqa: E402
from input.input_manager import Action, ActionFrame  # noqa: E402
from rendering.camera import Camera  # noqa: E402
from utils.config_loader import ConfigLoader  # noqa: E402
from world.stage import StageConfig  # noqa: E402
from world.stage_generator import generate_stage  # noqa: E402
from world.stage_manager import StageManager  # noqa: E402

OUT = Path(__file__).resolve().parent / "screenshots"
OUT.mkdir(exist_ok=True)
DT = 1.0 / 60.0
VIEWPORT = (1280, 720)
ATTACK = frozenset({Action.PRIMARY_ATTACK})
EMPTY = frozenset()
CATEGORIES = (
    "player", "classes", "combat", "weapons", "abilities", "passives",
    "boons", "items", "enemies", "loot", "world", "village", "npcs",
    "progression", "unlocks",
)


def _save(game: Game, name: str) -> None:
    import pygame

    path = OUT / f"{name}.png"
    pygame.image.save(game.renderer._screen, str(path))  # type: ignore[attr-defined]
    print(f"saved: {path}")


def _build_stage_scene(game: Game, registry: ContentRegistry, config: ConfigLoader):
    """Stage scene like main.py: seeded stage, warrior loadout."""
    stage_config = StageConfig.from_document(registry.get("world", "first_stage"))
    stage_data = generate_stage(stage_config, registry, seed=42)
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
    scene.begin_run(seed=42)
    scene._apply_class_loadout("warrior")
    return scene, manager


def _walk_to_boss(scene: PlaytestScene, manager: StageManager) -> None:
    """Walk rightmost doors until the boss floor is reached."""
    floors = len(manager.stage_data.floors)
    safety = 0
    while manager.floor_index < floors - 1 and safety < 200:
        # Kill anything alive (so the walk isn't blocked by rewards/encounters).
        if scene.room.kind == "boss" and scene._boss is not None and scene._boss.alive:
            scene._boss.health = 0.0
            scene._encounter.on_enemy_died()
        for enemy, _ai in scene.enemies:
            if enemy.alive:
                enemy.health = 0.0
                scene._encounter.on_enemy_died()
        if scene._reward_pending:
            scene.update(ActionFrame(aim_x=1.0), DT)
            scene.update(ActionFrame(), DT)
            continue
        door = max(scene.room.doors, key=lambda d: d.box.x)
        scene.player.body.teleport(
            door.box.x + 8.0, door.box.y + door.box.height / 2.0
        )
        scene.update(ActionFrame(), DT)
        safety += 1


def main() -> None:
    registry = ContentRegistry()
    for cat in CATEGORIES:
        registry.register_all(load_category(cat))
    config = ConfigLoader()
    game = Game(config=config)
    scene, manager = _build_stage_scene(game, registry, config)

    # --- Combat room: fight a couple of dummies up close ---
    # Walk one room in; teleport near enemies; swing a few times.
    door = max(scene.room.doors, key=lambda d: d.box.x)
    scene.player.body.teleport(door.box.x + 8.0, door.box.y + door.box.height / 2.0)
    scene.update(ActionFrame(), DT)
    # Move next to the first enemy and attack a few times.
    if scene.enemies:
        ex, ey = scene.enemies[0][0].body.x, scene.enemies[0][0].body.y
        scene.player.body.teleport(ex - 40, ey)
        scene.player.set_aim(1.0, 0.0)
    for _ in range(12):
        scene.update(ActionFrame(pressed=ATTACK, aim_x=1.0, aim_y=0.0), DT)
    scene.render(game.renderer)
    game.renderer.present()
    _save(game, "05_combat_room")

    # --- Boss fight: walk to boss floor ---
    _walk_to_boss(scene, manager)
    assert scene.room.kind == "boss", f"not on boss floor: {scene.room.kind}"
    assert scene._boss is not None, "boss not spawned"
    # Position player near the boss, let the boss act for a second.
    bx, by = scene._boss.body.x, scene._boss.body.y
    scene.player.body.teleport(bx - 70, by)
    scene.player.set_aim(1.0, 0.0)
    for _ in range(45):  # ~0.75s: boss winds up / attacks
        scene.update(ActionFrame(), DT)
    scene.render(game.renderer)
    game.renderer.present()
    _save(game, "06_boss_fight")

    # --- Boss phase 2: drop below 50% HP ---
    scene._boss.health = scene._boss.config.max_health * 0.4
    scene._boss_ai.update(scene.player.body.x, scene.player.body.y, DT)  # phase check
    for _ in range(60):  # phase 2: faster attacks + AoE
        scene.update(ActionFrame(), DT)
    scene.render(game.renderer)
    game.renderer.present()
    _save(game, "07_boss_phase2")

    game.renderer.close()
    print("done")


if __name__ == "__main__":
    main()
