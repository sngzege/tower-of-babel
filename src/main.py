"""Application entry point (Phase 15: full vertical-slice loop).

Default flow: MAIN MENU → VILLAGE → DUNGEON → (death/victory) → VILLAGE.
The AppContext owns the meta-game state (village + NPCs + progression) and
scene construction; this module only loads content, builds the context, and
starts the engine. Test modes (--village, --combat-test, --stage) bypass the
menu for quick iteration.

The ``--headless``/``--frames`` flags keep automated smoke tests possible.
"""

from __future__ import annotations

import argparse
import os

from core.constants import LOGS_DIR
from core.content_registry import ContentRegistry
from core.data_loader import load_category
from core.enums import SceneID
from engine.game import Game
from gameplay.app_context import AppContext
from gameplay.combat.attack import AttackData
from gameplay.player.player import Player
from gameplay.player.player_stats import PlayerStats
from gameplay.playtest_scene import PlaytestScene
from rendering.camera import Camera
from utils.config_loader import ConfigLoader
from utils.logger import get_logger, setup_logging
from world.stage import StageConfig
from world.stage_generator import generate_stage
from world.stage_manager import StageManager

_logger = get_logger(__name__)

CONTENT_CATEGORIES = (
    "player",
    "classes",
    "combat",
    "weapons",
    "abilities",
    "passives",
    "boons",
    "items",
    "enemies",
    "loot",
    "world",
    "village",
    "npcs",
    "progression",
    "unlocks",
)
PLAYER_STATS_ID = "player_base"
DEFAULT_STAGE_ID = "first_stage"


def _load_registry() -> ContentRegistry:
    registry = ContentRegistry()
    for category in CONTENT_CATEGORIES:
        try:
            registry.register_all(load_category(category))
        except Exception as exc:
            _logger.warning("Category '%s' failed to load: %s", category, exc)
    _logger.info(
        "Content registered: %s",
        {category: registry.count(category) for category in CONTENT_CATEGORIES},
    )
    return registry


def _build_stage_scene(
    game: Game, registry: ContentRegistry, config: ConfigLoader, stage_id: str
) -> PlaytestScene:
    """Legacy direct-dungeon scene (--stage test mode)."""
    stage_config = StageConfig.from_document(registry.get("world", stage_id))
    stage_data = generate_stage(stage_config, registry, seed=42)
    stage_manager = StageManager(stage_data)
    start_room = stage_manager.start()
    world = start_room.build_collision_world()
    spawn_x, spawn_y = start_room.player_spawn
    player = Player(
        stats=PlayerStats.from_document(registry.get("player", PLAYER_STATS_ID)),
        x=spawn_x,
        y=spawn_y,
        events=game.events,
        attack_data=AttackData.from_document(
            registry.get("combat", "player_default_attack")
        ),
    )
    camera_config = config.load("display").get("camera", {})
    camera = Camera(
        viewport_size=game.renderer.size,
        zoom=float(camera_config.get("zoom", 1.0)),
        follow_stiffness=float(camera_config.get("follow_stiffness", 8.0)),
        bounds=start_room.bounds,
    )
    return PlaytestScene(
        player=player,
        room=start_room,
        world=world,
        camera=camera,
        registry=registry,
        stage_manager=stage_manager,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Project bootstrap (Phase 15).")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--frames", type=int, default=None, help="stop after N frames")
    parser.add_argument(
        "--headless", action="store_true", help="use the dummy SDL video driver"
    )
    parser.add_argument(
        "--combat-test",
        action="store_true",
        help="spawn in a combat room with enemies for quick testing",
    )
    parser.add_argument(
        "--village",
        action="store_true",
        help="spawn directly in the village hub scene (skip menu)",
    )
    parser.add_argument(
        "--stage",
        default=None,
        help="spawn directly in a stage (skip menu); default: first_stage",
    )
    args = parser.parse_args(argv)

    if args.headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    setup_logging(args.log_level, LOGS_DIR / "game.log")
    _logger.info("Bootstrap starting (mode=%s)", "stage" if args.stage else "menu")

    config = ConfigLoader()
    registry = _load_registry()

    game = Game(config=config, vsync=False if args.headless else None)

    # -- Direct test modes (bypass menu) --
    if args.combat_test:
        from gameplay.enemies.enemy_factory import build_enemy
        from world.room import Room

        combat_room = Room.from_document(registry.get("world", "greybox_combat_hall"))
        world = combat_room.build_collision_world()
        spawn_x, spawn_y = combat_room.player_spawn
        player = Player(
            stats=PlayerStats.from_document(registry.get("player", PLAYER_STATS_ID)),
            x=spawn_x,
            y=spawn_y,
            events=game.events,
            attack_data=AttackData.from_document(
                registry.get("combat", "player_default_attack")
            ),
        )
        camera_config = config.load("display").get("camera", {})
        camera = Camera(
            viewport_size=game.renderer.size,
            zoom=float(camera_config.get("zoom", 1.0)),
            follow_stiffness=float(camera_config.get("follow_stiffness", 8.0)),
            bounds=combat_room.bounds,
        )
        enemies: list = []
        spawn_positions = combat_room.enemy_spawns or [
            (420, 200), (540, 200), (420, 360), (540, 360),
            (480, 280),
        ]
        for i, (sx, sy) in enumerate(spawn_positions):
            if i == 4:
                enemies.append(build_enemy(registry, "greybox_elite", x=sx, y=sy))
            else:
                enemies.append(build_enemy(registry, "greybox_dummy", x=sx, y=sy))
        game.register_scene(
            PlaytestScene(
                player=player,
                room=combat_room,
                world=world,
                camera=camera,
                registry=registry,
                stage_manager=None,
                enemies=enemies,
            ),
            initial=True,
        )
        game.run(max_frames=args.frames)
        _logger.info("Combat test complete")
        return 0

    if args.stage or args.village:
        from gameplay.persistent_state import PersistentState
        from gameplay.village.village_scene import VillageScene
        from world.room import Room

        app = AppContext(game=game, config=config, registry=registry)
        app.persistent = PersistentState.from_save(
            village_documents=registry.all("village"),
            npc_documents=registry.all("npcs"),
            mastery_documents=registry.all("progression"),
            unlock_documents=registry.all("unlocks"),
        )
        if args.stage and not args.village:
            game.register_scene(
                _build_stage_scene(game, registry, config, args.stage),
                initial=True,
            )
        else:
            room = Room.from_document(registry.get("world", "greybox_village"))
            world = room.build_collision_world()
            spawn_x, spawn_y = room.player_spawn
            player = Player(
                stats=PlayerStats.from_document(registry.get("player", PLAYER_STATS_ID)),
                x=spawn_x,
                y=spawn_y,
                events=game.events,
                attack_data=AttackData.from_document(
                    registry.get("combat", "player_default_attack")
                ),
            )
            camera_config = config.load("display").get("camera", {})
            camera = Camera(
                viewport_size=game.renderer.size,
                zoom=float(camera_config.get("zoom", 1.0)),
                follow_stiffness=float(camera_config.get("follow_stiffness", 8.0)),
                bounds=room.bounds,
            )
            game.register_scene(
                VillageScene(
                    player=player,
                    room=room,
                    world=world,
                    camera=camera,
                    village=app.persistent.village,
                    npc_service=app.persistent.npcs,
                    registry=registry,
                ),
                initial=True,
            )
        game.run(max_frames=args.frames)
        _logger.info("Direct mode complete")
        return 0

    # -- Full vertical-slice loop: menu → village → dungeon --
    app = AppContext(game=game, config=config, registry=registry)
    app.build_menu_scene()
    app.build_village_scene()
    game.scenes.switch_to(SceneID.MAIN_MENU)
    game.run(max_frames=args.frames)
    _logger.info("Bootstrap complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
