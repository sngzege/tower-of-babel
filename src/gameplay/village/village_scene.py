"""Village scene: walkable greybox hub (Phase 11 + 15).

The village is a real walkable space (not a menu): the player moves through
a Room built from data/world/rooms/greybox_village.yaml, and each building
plot is drawn from its data/village/buildings document. Building tier is
visual (plot -> tier1 tint) and functional (services/NPCs arrive in later
phases). Interacting (INTERACT/F) with a building attempts its next upgrade
and reports the result on screen.

Phase 15 additions:
  - NPCs are rendered near their building (arrived ones only) and F talks
    to the nearest NPC (service dialogue + run_prep heal).
  - The bottom-center gate starts a run (on_enter_dungeon callback).

Greybox scope (RULES.md §0): tinted rects, neutral names, no lore.
"""

from __future__ import annotations

from collections.abc import Callable

from core.content_registry import ContentRegistry
from core.enums import SceneID
from engine.scene import Scene
from gameplay.player.aim_controller import AimController
from gameplay.player.player import Player
from gameplay.player.player_controller import PlayerController
from gameplay.village.building import Building
from gameplay.village.npc import NPC, NPCService
from gameplay.village.village import GOLD, RELIC, VillageState
from input.input_manager import Action, ActionFrame
from physics.collision import AABB, CollisionWorld
from rendering.camera import Camera
from rendering.renderer import Color, Renderer
from utils.logger import get_logger
from world.room import Room

_logger = get_logger(__name__)

_FLOOR_COLOR: Color = (26, 30, 26)
_GRASS_COLOR: Color = (34, 44, 34)
_WALL_COLOR: Color = (24, 28, 48)  # dark Babylon stone
_PLOT_COLOR: Color = (70, 70, 80)
_TIER1_COLOR: Color = (70, 130, 200)
_BUILDING_FRAME: Color = (20, 20, 28)
_TEXT_COLOR: Color = (230, 230, 235)
_HINT_COLOR: Color = (170, 200, 170)
_MSG_OK: Color = (110, 220, 110)
_MSG_ERR: Color = (230, 110, 110)
_PLAYER_COLOR: Color = (150, 195, 250)
_DUNGEON_DOOR_COLOR: Color = (120, 70, 60)
_NPC_COLOR: Color = (240, 220, 140)
_NPC_ARRIVED_COLOR: Color = (140, 230, 160)

# Building visual tiers -> tint (greybox only, not a content decision).
_TIER_TINTS: dict[str, Color] = {
    "plot": _PLOT_COLOR,
    "tier1": _TIER1_COLOR,
}

# NPC spawn offset relative to their building's plot rect center.
_NPC_OFFSET_X = 0.0
_NPC_OFFSET_Y = 40.0


class VillageScene(Scene):
    """Walkable village hub with tiered building plots and service NPCs."""

    scene_id = SceneID.VILLAGE

    def __init__(
        self,
        player: Player,
        room: Room,
        world: CollisionWorld,
        camera: Camera,
        village: VillageState,
        registry: ContentRegistry | None = None,
        controller: PlayerController | None = None,
        npc_service: NPCService | None = None,
        on_enter_dungeon: Callable[[], None] | None = None,
    ) -> None:
        self.player = player
        self.room = room
        self.world = world
        self.camera = camera
        self.village = village
        self._registry = registry
        self._controller = controller or PlayerController()
        self._aim = AimController(screen_to_world=camera.screen_to_world)
        self._message = ""
        self._message_timer = 0.0
        self._message_is_error = False
        self._hovered_building: Building | None = None
        self._hovered_npc: NPC | None = None
        self._npc_service = npc_service
        self._on_enter_dungeon = on_enter_dungeon
        # Dungeon entrance: bottom-center gap in the wall. The player walks
        # through it to start a run (Phase 15 wires the transition).
        self._dungeon_door_rect = AABB(560.0, 776.0, 160.0, 24.0)

    # -- Interaction --

    def _nearest_building(self, max_dist: float = 90.0) -> Building | None:
        """The building the player is standing near, if any."""
        px, py = self.player.body.x, self.player.body.y
        nearest: Building | None = None
        best = max_dist
        for building in self.village.buildings.values():
            rect = building.plot_rect
            if rect is None:
                continue
            bx, by, bw, bh = rect
            # Distance from player center to the rect's center.
            cx, cy = bx + bw / 2.0, by + bh / 2.0
            dist = ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5
            if dist < best:
                best = dist
                nearest = building
        return nearest

    def _nearest_npc(self, max_dist: float = 80.0) -> NPC | None:
        """The nearest arrived NPC, if the player is close enough."""
        if self._npc_service is None:
            return None
        px, py = self.player.body.x, self.player.body.y
        nearest: NPC | None = None
        best = max_dist
        for npc in self._npc_service.arrived_npcs():
            pos = self._npc_position(npc)
            if pos is None:
                continue
            dist = ((px - pos[0]) ** 2 + (py - pos[1]) ** 2) ** 0.5
            if dist < best:
                best = dist
                nearest = npc
        return nearest

    def _npc_position(self, npc: NPC) -> tuple[float, float] | None:
        """Where the NPC stands (in front of their building)."""
        building = self.village.buildings.get(npc.building_id)
        if building is None or building.plot_rect is None:
            return None
        bx, by, bw, bh = building.plot_rect
        return (bx + bw / 2.0 + _NPC_OFFSET_X, by + bh + _NPC_OFFSET_Y)

    def _try_upgrade(self, building: Building) -> None:
        """Attempt the building's next upgrade; show a message either way."""
        try:
            upgraded = self.village.upgrade_building(building.building_id)
        except Exception as exc:
            self._message = str(exc)
            self._message_is_error = True
            _logger.info("Village upgrade failed: %s", exc)
            return
        self._message = f"{upgraded.name} upgraded to tier {upgraded.current_tier + 1}"
        self._message_is_error = False
        _logger.info("Village upgrade OK: %s", self._message)

    def _talk_to_npc(self, npc: NPC) -> None:
        """Run the NPC's service (greybox): dialogue line + simple effect."""
        line = npc.dialogue_line("greeting", "...")
        self._message = f"{npc.name}: {line}"
        self._message_is_error = False
        # Service effects (greybox placeholders):
        if npc.service == "run_prep":
            self.player.health = self.player.stats.max_health
            self._message = f"{npc.name}: Restored your health for the run."
            _logger.info("NPC run_prep: player healed")
        elif npc.service == "loadout":
            options = npc.service_options()
            if options:
                self._message = f"{npc.name}: Expanded loadout options: {', '.join(options)}"
        elif npc.service == "upgrades":
            options = npc.service_options()
            if options:
                self._message = f"{npc.name}: New upgrade options: {', '.join(options)}"

    def _try_enter_dungeon(self) -> bool:
        """True when the player overlaps the dungeon entrance gap."""
        return self.player.body.box.intersects(self._dungeon_door_rect)

    # -- Update --

    def update(self, frame: ActionFrame, dt: float) -> None:
        aim = self._aim.resolve(frame, self.player.body.x, self.player.body.y)
        self.player.set_aim(aim.direction[0], aim.direction[1])
        intent = self._controller.build_intent(frame)
        self.player.update(intent, self.world, dt)

        self._hovered_building = self._nearest_building()
        self._hovered_npc = self._nearest_npc()

        if Action.INTERACT in frame.pressed:
            if self._hovered_npc is not None:
                self._talk_to_npc(self._hovered_npc)
            elif self._hovered_building is not None:
                self._try_upgrade(self._hovered_building)

        if self._try_enter_dungeon() and self._on_enter_dungeon is not None:
            self._on_enter_dungeon()
            return

        if self._message_timer > 0.0:
            self._message_timer -= dt
            if self._message_timer <= 0.0:
                self._message = ""

        self.camera.follow(self.player.body.x, self.player.body.y, dt)

    # -- Render --

    def render(self, renderer: Renderer) -> None:
        # Grass/floor tiles (32x32 sprite).
        tile = 32
        tw, th = self.room.width, self.room.height
        for ty in range(0, int(th), tile):
            for tx in range(0, int(tw), tile):
                sx, sy = self.camera.world_to_screen(tx, ty)
                renderer.draw_image("tile_floor", int(sx), int(sy), scale=1)
        for solid in self.room.solids:
            renderer.draw_rect(self.camera.screen_rect(solid), _WALL_COLOR)

        # Dungeon entrance marker (bottom-center).
        renderer.draw_rect(
            self.camera.screen_rect(self._dungeon_door_rect), _DUNGEON_DOOR_COLOR
        )

        # Building plots.
        for building in self.village.buildings.values():
            rect = building.plot_rect
            if rect is None:
                continue
            bx, by, bw, bh = rect
            sprite_id = "building_tier1" if building.visual_state == "tier1" else "building_plot"
            # Sprite feet align with the plot bottom; scale to fit plot width.
            scale = max(1, int(bw / 32))
            sx, sy = self.camera.world_to_screen(bx, by + bh - 32 * scale)
            renderer.draw_image(sprite_id, int(sx), int(sy), scale=scale)
            # Hover frame.
            if building is self._hovered_building:
                renderer.draw_rect(self.camera.screen_rect(AABB(bx, by, bw, bh)), (255, 255, 255))
            # Building name + tier.
            label = f"{building.name}  T{building.current_tier + 1}"
            lx, ly = self.camera.world_to_screen(bx + 8, by + 8)
            renderer.draw_text(label, int(lx), int(ly), _TEXT_COLOR, 14)

        # NPCs (arrived only) in front of their buildings.
        if self._npc_service is not None:
            for npc in self._npc_service.arrived_npcs():
                pos = self._npc_position(npc)
                if pos is None:
                    continue
                sx, sy = self.camera.world_to_screen(*pos)
                scale = max(1, int(self.camera.zoom))
                npc_sprite = {
                    "loadout": "npc_loadout",
                    "run_prep": "npc_run_prep",
                    "upgrades": "npc_upgrades",
                }.get(npc.service, "npc")
                renderer.draw_image(
                    npc_sprite, int(sx - 8 * scale), int(sy - 16 * scale), scale=scale
                )
                renderer.draw_text(
                    npc.name, int(sx - 12), int(sy - 18 * scale), _TEXT_COLOR, 11
                )

        # Player.
        px, py = self.player.body.x, self.player.body.y
        pw, ph = self.player.body.width, self.player.body.height
        psx, psy = self.camera.world_to_screen(px - pw / 2, py - ph / 2)
        scale = max(1, int(self.camera.zoom))
        renderer.draw_image("player", int(psx), int(psy), scale=scale)

        # HUD: village resources + town level.
        w, h = renderer.size
        gold = self.village.resources.get(GOLD, 0)
        relics = self.village.resources.get(RELIC, 0)
        renderer.draw_text(
            f"Town Lv {self.village.town_level}    Gold {gold}    Relics {relics}",
            20, 20, _TEXT_COLOR, 16,
        )
        renderer.draw_text(
            "WASD move  |  F: interact (talk / upgrade)",
            20, h - 34, _HINT_COLOR, 13,
        )
        renderer.draw_text(
            "Walk to the bottom-center gate to enter the dungeon",
            20, h - 18, _HINT_COLOR, 12,
        )

        if self._hovered_npc is not None:
            sx, sy = self.camera.world_to_screen(*self._npc_position(self._hovered_npc) or (0, 0))  # noqa: E501
            renderer.draw_text("[F] Talk", int(sx - 18), int(sy + 16), (255, 220, 120), 12)
        elif self._hovered_building is not None:
            rect = self._hovered_building.plot_rect
            if rect is not None:
                sx, sy = self.camera.world_to_screen(
                    rect[0] + rect[2] / 2.0 - 60, rect[1] - 24
                )
                renderer.draw_text(
                    "[F] Upgrade  (1 Relic)", int(sx), int(sy), (255, 220, 120), 12
                )

        if self._message:
            color = _MSG_OK if not self._message_is_error else _MSG_ERR
            renderer.draw_text(self._message, w // 2 - 220, h // 2, color, 16)
