"""Application entry point (Phase 6: greybox floor traversal).

Loads configuration and content, builds a floor from the FloorGraph prototype
and FloorAssembler, and runs the engine loop. The ``--headless``/``--frames``
flags keep automated smoke tests possible.
"""

from __future__ import annotations

import argparse
import os

from core.constants import LOGS_DIR
from core.content_registry import ContentRegistry
from core.data_loader import load_category
from engine.game import Game
from gameplay.player.player import Player
from gameplay.player.player_stats import PlayerStats
from gameplay.playtest_scene import PlaytestScene
from rendering.camera import Camera
from utils.config_loader import ConfigLoader
from utils.logger import get_logger, setup_logging
from world.dungeon_generator import generate_floor_graph
from world.floor_assembler import assemble_floor

_logger = get_logger(__name__)

CONTENT_CATEGORIES = ("player", "weapons", "items", "enemies", "loot", "world")
PLAYER_STATS_ID = "player_base"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Project bootstrap (Phase 6).")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--frames", type=int, default=None, help="stop after N frames")
    parser.add_argument(
        "--headless", action="store_true", help="use the dummy SDL video driver"
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="floor generation seed"
    )
    args = parser.parse_args(argv)

    if args.headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    setup_logging(args.log_level, LOGS_DIR / "game.log")
    _logger.info("Bootstrap starting (seed=%s)", args.seed)

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

    # Generate a floor graph and assemble it into playable rooms.
    # Uses the seeded RNG prototype from Phase 1 — deterministic per seed.
    floor_graph = generate_floor_graph(args.seed)

    _logger.info(
        "Floor graph: %d rooms, start=%d, boss=%d",
        len(floor_graph.rooms),
        floor_graph.start_uid,
        floor_graph.boss_uid,
    )

    floor_data = assemble_floor(floor_graph, registry, seed=args.seed)

    start_room = floor_data.rooms[floor_data.start_room_id]
    world = start_room.build_collision_world()
    spawn_x, spawn_y = start_room.player_spawn
    player = Player(stats=PlayerStats.from_document(
        registry.get("player", PLAYER_STATS_ID)
    ), x=spawn_x, y=spawn_y, events=game.events)

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
            floor_data=floor_data,
        ),
        initial=True,
    )
    game.run(max_frames=args.frames)
    _logger.info("Bootstrap complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
