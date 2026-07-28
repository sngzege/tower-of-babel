"""Application entry point (Phase 7: data-driven multi-floor stage).

Loads configuration and content, parses the requested stage document from
the ContentRegistry, generates the full stage (seeded, deterministic), and
runs the engine loop. The stage structure is never hardcoded here — it
comes from data/world/stages/*.yaml through the data-driven pipeline.
The ``--headless``/``--frames`` flags keep automated smoke tests possible.
"""

from __future__ import annotations

import argparse
import os

from core.constants import LOGS_DIR
from core.content_registry import ContentRegistry
from core.data_loader import load_category
from engine.game import Game
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
)
PLAYER_STATS_ID = "player_base"
DEFAULT_STAGE_ID = "first_stage"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Project bootstrap (Phase 7).")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--frames", type=int, default=None, help="stop after N frames")
    parser.add_argument(
        "--headless", action="store_true", help="use the dummy SDL video driver"
    )
    parser.add_argument("--seed", type=int, default=42, help="stage generation seed")
    parser.add_argument(
        "--stage",
        default=DEFAULT_STAGE_ID,
        help="stage content id from data/world/stages",
    )
    args = parser.parse_args(argv)

    if args.headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    setup_logging(args.log_level, LOGS_DIR / "game.log")
    _logger.info("Bootstrap starting (stage=%s, seed=%s)", args.stage, args.seed)

    config = ConfigLoader()
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

    game = Game(config=config, vsync=False if args.headless else None)

    # Load the stage definition from data and generate every floor.
    stage_config = StageConfig.from_document(registry.get("world", args.stage))
    stage_data = generate_stage(stage_config, registry, seed=args.seed)
    _logger.info(
        "Stage '%s': %d floor(s), rooms per floor: %s",
        stage_config.stage_id,
        stage_data.floor_count,
        [len(floor.rooms) for floor in stage_data.floors],
    )

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

    game.register_scene(
        PlaytestScene(
            player=player,
            room=start_room,
            world=world,
            camera=camera,
            registry=registry,
            stage_manager=stage_manager,
        ),
        initial=True,
    )
    game.run(max_frames=args.frames)
    _logger.info("Bootstrap complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
