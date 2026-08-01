"""Phase 15 integration: the full vertical-slice loop.

Drives the real AppContext + SceneManager (no pygame — RecordingRenderer +
scripted ActionFrames) through the complete loop:

    menu → village → dungeon (5 floors) → boss → death/victory → village
    → building upgrade / NPC tier → new run with new options → save persists

Verifies VERTICAL_SLICE.md §4 acceptance criteria headlessly:
  1. start in village, prepare, enter dungeon
  5. boss gates progress; beating it grants a trophy (relic)
  6. returning applies results: a building visibly upgrades, NPC service
     tier increases
  7. a new run starts with new options; save/load survives a "restart"
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Keep pygame headless during integration tests (no window needed).
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from core.content_registry import ContentRegistry  # noqa: E402
from core.data_loader import load_category  # noqa: E402
from core.enums import SceneID  # noqa: E402
from engine.game import Game  # noqa: E402
from gameplay.app_context import AppContext  # noqa: E402
from gameplay.playtest_scene import PlaytestScene  # noqa: E402
from gameplay.village.village import RELIC  # noqa: E402
from input.input_manager import Action, ActionFrame  # noqa: E402
from save.save_slots import SlotManager  # noqa: E402
from utils.config_loader import ConfigLoader  # noqa: E402

DT = 1.0 / 60.0
VIEWPORT = (320, 180)

CATEGORIES = (
    "player", "classes", "combat", "weapons", "abilities", "passives",
    "boons", "items", "enemies", "loot", "world", "village", "npcs",
    "progression", "unlocks",
)


class RecordingRenderer:
    """Renderer-protocol test double (framework-free)."""

    @property
    def size(self) -> tuple[int, int]:
        return VIEWPORT

    def draw_rect(self, rect, color) -> None:  # noqa: ANN001
        pass

    def draw_text(self, text, x, y, color, font_size=12) -> None:  # noqa: ANN001
        pass

    def clear(self, color) -> None:  # noqa: ANN001
        pass

    def present(self) -> None:
        pass

    def tick(self, fps: int) -> float:
        return DT

    def close(self) -> None:
        pass


class _FakeRenderer:
    """Stand-in for PygameRenderer so AppContext can build cameras."""

    def __init__(self) -> None:
        self.size = VIEWPORT


def _build_app(tmp_path: Path) -> tuple[AppContext, Game]:
    registry = ContentRegistry()
    for category in CATEGORIES:
        registry.register_all(load_category(category))
    config = ConfigLoader()
    game = Game(config=config)
    game.renderer.close()  # release the real window; tests never draw
    game.renderer = _FakeRenderer()  # type: ignore[assignment]
    slots = SlotManager(saves_dir=tmp_path, slot_count=1)
    return AppContext(game=game, config=config, registry=registry, slots=slots), game


def _press(scene, action: Action) -> None:
    scene.update(ActionFrame(pressed=frozenset({action})), DT)


def _walk_to_next_room(scene: PlaytestScene) -> None:
    door = max(scene.room.doors, key=lambda d: d.box.x)
    scene.player.body.teleport(
        door.box.x + 8.0, door.box.y + door.box.height / 2.0
    )
    scene.update(ActionFrame(), DT)


def _kill_current_boss(scene: PlaytestScene) -> None:
    if scene._boss is not None and scene._boss.alive:
        scene._boss.health = 0.0
        scene._encounter.on_enemy_died()


def test_full_vertical_slice_loop(tmp_path: Path) -> None:
    app, game = _build_app(tmp_path)
    app.load_persistent()

    # --- Menu → village ---
    app.build_menu_scene()
    app.build_village_scene()
    game.scenes.switch_to(SceneID.MAIN_MENU)
    assert game.scenes.active.scene_id is SceneID.MAIN_MENU
    _press(game.scenes.active, Action.INTERACT)  # F = new game
    assert game.scenes.active.scene_id is SceneID.VILLAGE

    # --- Village: walkable hub, building visible at tier 0 ---
    village_scene = game.scenes.active
    assert village_scene.village.building_tier("building_a") == 0
    # NPCs have not arrived before the first boss kill.
    assert app.persistent.npcs.arrived_npcs() == ()

    # --- Enter the dungeon through the bottom gate ---
    village_scene.player.body.teleport(640.0, 790.0)  # on the gate
    village_scene.update(ActionFrame(), DT)
    assert game.scenes.active.scene_id is SceneID.DUNGEON
    dungeon = game.scenes.active
    assert isinstance(dungeon, PlaytestScene)
    assert len(dungeon._stage_manager.stage_data.floors) == 5  # L7: 4 + boss

    # --- Walk the whole run: rooms → floors → boss ---
    MAX_STEPS = 96
    for _ in range(MAX_STEPS):
        if dungeon._run.ended:
            break
        if dungeon.room.kind == "boss":
            _kill_current_boss(dungeon)
        _walk_to_next_room(dungeon)
        # Skip the reward overlay if it appeared (choose the first card).
        if dungeon._reward_pending:
            dungeon.update(ActionFrame(aim_x=1.0), DT)
            dungeon.update(ActionFrame(), DT)

    assert dungeon._run.ended, "run did not end during the walk"
    assert dungeon._run.state.phase.value == "victory"

    # --- Return to the village; results applied + saved ---
    dungeon.update(ActionFrame(), DT)  # _finish_run fires (on_run_finished)
    assert game.scenes.active.scene_id is SceneID.VILLAGE
    assert app.persistent.progression.has_milestone("first_boss_kill")
    assert app.persistent.village.resources[RELIC] >= 1  # boss trophy banked
    # NPCs arrived + service tier advanced (acceptance criterion 6).
    assert {npc.npc_id for npc in app.persistent.npcs.arrived_npcs()} == {
        "npc_a", "npc_b", "npc_c",
    }
    assert app.persistent.npcs.get("npc_a").service_tier == 1
    # Save file was written at the village (D15).
    assert app.slots.exists(0)

    # --- Village upgrade: spend the relic on a building ---
    village_scene = game.scenes.active
    building = village_scene.village.get_building("building_a")
    before = building.current_tier
    upgraded = village_scene.village.upgrade_building("building_a")
    assert upgraded.current_tier == before + 1
    assert village_scene.village.get_building("building_a").visual_state == "tier1"
    app.save_at_village()

    # --- New run starts with new options (acceptance criterion 7) ---
    app.build_dungeon_scene(checkpoint=None)
    game.scenes.switch_to(SceneID.DUNGEON)
    dungeon = game.scenes.active
    assert isinstance(dungeon, PlaytestScene)
    # Unlocked boon pool now includes the boss-granted boon.
    assert "boon_weapon_damage" in dungeon._unlocked_boons
    # Run-start bonuses from mastery are applied (L15).
    assert dungeon._run.build.max_health_bonus > 0 or dungeon._run.build.damage_mult > 1.0

    # --- "Restart" the app: save/load survives (criterion 7) ---
    fresh_app, fresh_game = _build_app(tmp_path)
    fresh_app.load_persistent()
    assert fresh_app.persistent.progression.has_milestone("first_boss_kill")
    assert fresh_app.persistent.village.building_tier("building_a") == 1
    assert fresh_app.persistent.npcs.get("npc_a").service_tier == 1
    assert fresh_app.persistent.village.resources[RELIC] == 0  # spent on upgrade


def test_death_returns_to_village_with_results(tmp_path: Path) -> None:
    """Death ends the run and returns to the village (no relic)."""
    app, game = _build_app(tmp_path)
    app.load_persistent()
    app.build_village_scene()
    game.scenes.switch_to(SceneID.VILLAGE)
    village_scene = game.scenes.active
    village_scene.player.body.teleport(640.0, 790.0)
    village_scene.update(ActionFrame(), DT)
    assert game.scenes.active.scene_id is SceneID.DUNGEON
    dungeon = game.scenes.active

    # Kill the player in the first room.
    dungeon.player.health = 0.0
    dungeon.player.die()
    dungeon.update(ActionFrame(), DT)
    assert dungeon._run.ended
    assert dungeon._run.state.phase.value == "death"
    # Return to village fires the run-finished callback.
    dungeon.update(ActionFrame(), DT)
    assert game.scenes.active.scene_id is SceneID.VILLAGE
    assert not app.persistent.progression.has_milestone("first_boss_kill")
    assert app.persistent.village.resources[RELIC] == 0
    # Run count still recorded (persistence works for failures too).
    assert app.persistent.progression.records["total_runs"] >= 1


def test_checkpoint_continue_resumes_mid_run(tmp_path: Path) -> None:
    """D15: quitting mid-run saves a checkpoint; continue restores it."""
    app, game = _build_app(tmp_path)
    app.load_persistent()
    app.build_village_scene()
    game.scenes.switch_to(SceneID.VILLAGE)
    village_scene = game.scenes.active
    village_scene.player.body.teleport(640.0, 790.0)
    village_scene.update(ActionFrame(), DT)
    dungeon = game.scenes.active
    assert isinstance(dungeon, PlaytestScene)

    # Advance one room: a checkpoint is emitted at the transition.
    _walk_to_next_room(dungeon)
    assert dungeon.room.kind == "combat"
    save = app.slots.read(0)
    assert save["run_state"] is not None
    assert save["run_state"]["phase"] == "active"

    # New app instance: menu offers continue; selecting it restores.
    fresh_app, fresh_game = _build_app(tmp_path)
    checkpoint = fresh_app.load_checkpoint()
    assert checkpoint is not None
    assert checkpoint.floor_index == 0
    fresh_app.persistent = fresh_app.load_persistent()
    fresh_app.build_dungeon_scene(checkpoint=checkpoint)
    fresh_game.scenes.switch_to(SceneID.DUNGEON)
    restored = fresh_game.scenes.active
    assert isinstance(restored, PlaytestScene)
    # Build + health carried over; run is active again.
    assert restored._run.build.weapon_id == dungeon._run.build.weapon_id
    assert restored.player.health == pytest.approx(dungeon.player.health)
    assert restored._run.state.phase.value == "active"
