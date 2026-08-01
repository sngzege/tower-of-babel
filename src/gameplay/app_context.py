"""App context: composition root for the meta-game (Phase 15).

Binds the persistent state (village + NPCs + progression), the save slots,
and the content registry to the scene flow. It owns *construction* of the
three playable scenes (menu → village → dungeon) and the transitions between
them, so main.py stays a thin bootstrap and scenes never import each other
(ARCHITECTURE.md §3: no lateral imports between gameplay scenes).

Transitions:
  - menu → village        (start / continue to hub)
  - village → dungeon     (walk through the dungeon gate)
  - dungeon → village     (death or boss victory: results applied, save)
"""

from __future__ import annotations

from typing import Any

from core.content_registry import ContentRegistry
from core.enums import SceneID
from engine.game import Game
from gameplay.combat.attack import AttackData
from gameplay.menu_scene import MenuScene
from gameplay.persistent_state import PersistentState
from gameplay.player.player import Player
from gameplay.player.player_stats import PlayerStats
from gameplay.playtest_scene import PlaytestScene
from gameplay.run_checkpoint import RunCheckpoint
from gameplay.village.village_scene import VillageScene
from rendering.camera import Camera
from save.save_slots import SlotManager
from utils.config_loader import ConfigLoader
from utils.logger import get_logger
from world.room import Room
from world.stage import StageConfig
from world.stage_generator import generate_stage
from world.stage_manager import StageManager

_logger = get_logger(__name__)

PLAYER_STATS_ID = "player_base"
STAGE_ID = "first_stage"
VILLAGE_ROOM_ID = "greybox_village"
DEFAULT_SLOT = 0


class AppContext:
    """Builds and switches scenes; owns meta-game state."""

    def __init__(
        self,
        game: Game,
        config: ConfigLoader,
        registry: ContentRegistry,
        slots: SlotManager | None = None,
    ) -> None:
        self.game = game
        self.config = config
        self.registry = registry
        self.slots = slots or SlotManager()
        # Persistent state is loaded lazily (from save if present).
        self.persistent: PersistentState | None = None
        self._dungeon_scene: PlaytestScene | None = None
        self._village_scene: VillageScene | None = None
        self._pending_checkpoint: RunCheckpoint | None = None
        self._save_callback = self._write_save

    # -- Persistent state --

    def load_persistent(self) -> PersistentState:
        """Load (or create) the persistent meta-game state from slot 0."""
        saved = self.slots.read_or_new(DEFAULT_SLOT).get("persistent") or {}
        self.persistent = PersistentState.from_save(
            village_documents=self.registry.all("village"),
            npc_documents=self.registry.all("npcs"),
            mastery_documents=self.registry.all("progression"),
            unlock_documents=self.registry.all("unlocks"),
            saved_persistent=saved if isinstance(saved, dict) else None,
        )
        return self.persistent

    def load_checkpoint(self) -> RunCheckpoint | None:
        """Load the saved run checkpoint (D15: resume mid-run), if any."""
        save = self.slots.read_or_new(DEFAULT_SLOT)
        run_state = save.get("run_state")
        if run_state is None:
            return None
        try:
            return RunCheckpoint.from_payload(run_state)
        except ValueError as exc:
            _logger.warning("Ignoring invalid run checkpoint: %s", exc)
            return None

    def _write_save(self, run_state: dict[str, Any] | None = None) -> None:
        """Persist the current meta-game state (and optional run checkpoint)."""
        if self.persistent is None:
            return
        from save.save_schema import new_save_template

        save = new_save_template()
        save["persistent"] = self.persistent.to_save()
        save["run_state"] = run_state
        self.slots.write(DEFAULT_SLOT, save)

    def save_at_village(self) -> None:
        """Save persistent state with no active run (D15: village save)."""
        self._write_save(run_state=None)

    def save_checkpoint(self, checkpoint: dict[str, Any]) -> None:
        """Save persistent state + a mid-run checkpoint (D15)."""
        self._write_save(run_state=checkpoint)

    # -- Scene construction --

    def _build_player(self, x: float, y: float) -> Player:
        return Player(
            stats=PlayerStats.from_document(
                self.registry.get("player", PLAYER_STATS_ID)
            ),
            x=x,
            y=y,
            events=self.game.events,
            attack_data=AttackData.from_document(
                self.registry.get("combat", "player_default_attack")
            ),
        )

    def _build_camera(self, bounds: Any) -> Camera:
        camera_config = self.config.load("display").get("camera", {})
        return Camera(
            viewport_size=self.game.renderer.size,
            zoom=float(camera_config.get("zoom", 1.0)),
            follow_stiffness=float(camera_config.get("follow_stiffness", 8.0)),
            bounds=bounds,
        )

    def build_menu_scene(self) -> MenuScene:
        has_save = self.slots.exists(DEFAULT_SLOT)
        checkpoint = self.load_checkpoint() if has_save else None
        self._pending_checkpoint = checkpoint
        scene = MenuScene(
            registry=self.registry,
            can_continue=checkpoint is not None,
            on_new_game=self._start_new_game,
            on_continue=self._continue_run,
        )
        self.game.scenes.replace(scene)
        return scene

    def build_village_scene(self) -> VillageScene:
        if self.persistent is None:
            self.load_persistent()
        assert self.persistent is not None
        room = Room.from_document(self.registry.get("world", VILLAGE_ROOM_ID))
        world = room.build_collision_world()
        spawn_x, spawn_y = room.player_spawn
        scene = VillageScene(
            player=self._build_player(spawn_x, spawn_y),
            room=room,
            world=world,
            camera=self._build_camera(room.bounds),
            village=self.persistent.village,
            npc_service=self.persistent.npcs,
            registry=self.registry,
            on_enter_dungeon=self._enter_dungeon,
        )
        self._village_scene = scene
        self.game.scenes.replace(scene)
        return scene

    def build_dungeon_scene(
        self, checkpoint: RunCheckpoint | None = None
    ) -> PlaytestScene:
        """Build the dungeon scene for a fresh run or a checkpoint resume."""
        stage_config = StageConfig.from_document(self.registry.get("world", STAGE_ID))
        stage_data = generate_stage(stage_config, self.registry, seed=42)
        manager = StageManager(stage_data)

        if checkpoint is not None:
            start_room = manager.resume_at(checkpoint.floor_index)
            player = self._build_player(*start_room.player_spawn)
            scene = PlaytestScene(
                player=player,
                room=start_room,
                world=start_room.build_collision_world(),
                camera=self._build_camera(start_room.bounds),
                registry=self.registry,
                stage_manager=manager,
                persistent=self.persistent,
                on_run_finished=self._return_to_village,
                on_checkpoint=self.save_checkpoint,
            )
            scene.restore_checkpoint(checkpoint)
        else:
            start_room = manager.start()
            player = self._build_player(*start_room.player_spawn)
            scene = PlaytestScene(
                player=player,
                room=start_room,
                world=start_room.build_collision_world(),
                camera=self._build_camera(start_room.bounds),
                registry=self.registry,
                stage_manager=manager,
                persistent=self.persistent,
                on_run_finished=self._return_to_village,
                on_checkpoint=self.save_checkpoint,
            )
            scene.begin_run(seed=42)
            # L15: every run begins with permanent bonuses + unlocked boons.
            scene.apply_run_start_bonuses(self.persistent)
        self._dungeon_scene = scene
        self.game.scenes.replace(scene)
        return scene

    # -- Transitions --

    def _start_new_game(self) -> None:
        self.persistent = self.load_persistent()
        self._pending_checkpoint = None
        self.save_at_village()
        # Rebuild the village scene so it points at the fresh persistent
        # state (the menu was built before load_persistent).
        self.build_village_scene()
        self.game.scenes.switch_to(SceneID.VILLAGE)

    def _continue_run(self) -> None:
        self.persistent = self.load_persistent()
        self.build_dungeon_scene(checkpoint=self._pending_checkpoint)
        self.game.scenes.switch_to(SceneID.DUNGEON)

    def _enter_dungeon(self) -> None:
        self.build_dungeon_scene(checkpoint=None)
        self.game.scenes.switch_to(SceneID.DUNGEON)

    def _return_to_village(self, result: object) -> None:
        """After a run ends: persist results, save, and go back to the hub."""
        assert self.persistent is not None
        self.save_at_village()
        self.game.scenes.switch_to(SceneID.VILLAGE)
