"""Capture real screenshots of the greybox game (menu / village / dungeon)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.content_registry import ContentRegistry  # noqa: E402
from core.data_loader import load_category  # noqa: E402
from core.enums import SceneID  # noqa: E402
from engine.game import Game  # noqa: E402
from gameplay.app_context import AppContext  # noqa: E402
from input.input_manager import ActionFrame  # noqa: E402
from utils.config_loader import ConfigLoader  # noqa: E402

OUT = Path(__file__).resolve().parent / "screenshots"
OUT.mkdir(exist_ok=True)

CATEGORIES = (
    "player", "classes", "combat", "weapons", "abilities", "passives",
    "boons", "items", "enemies", "loot", "world", "village", "npcs",
    "progression", "unlocks",
)
DT = 1.0 / 60.0


def _save(game: Game, name: str) -> None:
    import pygame

    path = OUT / f"{name}.png"
    pygame.image.save(game.renderer._screen, str(path))  # type: ignore[attr-defined]
    print(f"saved: {path}")


def main() -> None:
    registry = ContentRegistry()
    for cat in CATEGORIES:
        registry.register_all(load_category(cat))
    config = ConfigLoader()
    game = Game(config=config)
    app = AppContext(game=game, config=config, registry=registry)
    app.load_persistent()

    # --- MENU ---
    app.build_menu_scene()
    app.build_village_scene()
    game.scenes.switch_to(SceneID.MAIN_MENU)
    game.scenes.update(ActionFrame(), DT)
    game.scenes.render(game.renderer)
    game.renderer.present()
    _save(game, "01_menu")

    # --- VILLAGE (move player near a building so it's visible) ---
    game.scenes.switch_to(SceneID.VILLAGE)
    village = game.scenes.active
    village.player.body.teleport(640.0, 200.0)  # near building_a
    village.update(ActionFrame(), DT)
    village.render(game.renderer)
    game.renderer.present()
    _save(game, "02_village")

    # --- DUNGEON (first room) ---
    app._enter_dungeon()
    dungeon = game.scenes.active
    dungeon.update(ActionFrame(), DT)
    dungeon.render(game.renderer)
    game.renderer.present()
    _save(game, "03_dungeon")

    # --- DUNGEON with enemies + HUD (walk one room) ---
    door = max(dungeon.room.doors, key=lambda d: d.box.x)
    dungeon.player.body.teleport(door.box.x + 8.0, door.box.y + door.box.height / 2.0)
    dungeon.update(ActionFrame(), DT)
    dungeon.render(game.renderer)
    game.renderer.present()
    _save(game, "04_dungeon_combat")

    game.renderer.close()
    print("done")


if __name__ == "__main__":
    main()
