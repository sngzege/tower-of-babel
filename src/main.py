"""Application entry point (Phase 3: playable greybox slice).

Loads configuration and content, builds the greybox playtest scene (real
player, room, collision, follow camera - all data-driven), and runs the
engine loop. The ``--headless``/``--frames`` flags keep automated smoke
tests possible (IMPLEMENTATION_PLAN.md Phases 2-3).
"""

from __future__ import annotations

import argparse
import os

from core.constants import LOGS_DIR
from core.content_registry import ContentRegistry
from core.data_loader import load_category
from engine.game import Game
from gameplay.enemies.enemy_factory import build_enemy
from gameplay.player.player import Player
from gameplay.player.player_stats import PlayerStats
from gameplay.playtest_scene import PlaytestScene
from rendering.camera import Camera
from utils.config_loader import ConfigLoader
from utils.logger import get_logger, setup_logging
from world.room import Room

_logger = get_logger(__name__)

# Content categories the bootstrap attempts to load (PROVISIONAL - extend as
# new approved categories appear under data/).
CONTENT_CATEGORIES = ("player", "weapons", "items", "enemies", "loot", "world")

# The Phase 3 playable slice content ids (greybox; not procedural).
PLAYER_STATS_ID = "player_base"
GREYBOX_ROOM_ID = "greybox_arena"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Project bootstrap (Phase 3).")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--frames", type=int, default=None, help="stop after N frames")
    parser.add_argument(
        "--headless", action="store_true", help="use the dummy SDL video driver"
    )
    args = parser.parse_args(argv)

    if args.headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    setup_logging(args.log_level, LOGS_DIR / "game.log")
    _logger.info("Bootstrap starting")

    config = ConfigLoader()
    registry = ContentRegistry()
    for category in CONTENT_CATEGORIES:
        try:
            registry.register_all(load_category(category))
        except Exception as exc:  # data problems must surface loudly in development
            _logger.warning("Category '%s' failed to load: %s", category, exc)
    _logger.info(
        "Content registered: %s",
        {category: registry.count(category) for category in CONTENT_CATEGORIES},
    )

    game = Game(config=config, vsync=False if args.headless else None)

    # Playable slice: stats, room, player, camera - everything from data.
    stats = PlayerStats.from_document(registry.get("player", PLAYER_STATS_ID))
    room = Room.from_document(registry.get("world", GREYBOX_ROOM_ID))
    world = room.build_collision_world()
    spawn_x, spawn_y = room.player_spawn
    player = Player(stats=stats, x=spawn_x, y=spawn_y, events=game.events)

    camera_config = config.load("display").get("camera", {})
    camera = Camera(
        viewport_size=game.renderer.size,
        zoom=float(camera_config.get("zoom", 1.0)),
        follow_stiffness=float(camera_config.get("follow_stiffness", 8.0)),
        bounds=room.bounds,
    )
    # Phase 5: greybox enemies.
    enemies = [
        build_enemy(registry, "greybox_dummy", x=400.0, y=200.0),
        build_enemy(registry, "greybox_dummy", x=560.0, y=400.0),
    ]

    game.register_scene(
        PlaytestScene(
            player=player,
            room=room,
            world=world,
            camera=camera,
            enemies=enemies,
            registry=registry,
        ),
        initial=True,
    )
    game.run(max_frames=args.frames)
    _logger.info("Bootstrap complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
