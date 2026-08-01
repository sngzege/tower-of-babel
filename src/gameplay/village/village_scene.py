"""Village scene: walkable greybox hub (Phase 11).

The village is a real walkable space (not a menu): the player moves through
a Room built from data/world/rooms/greybox_village.yaml, and each building
plot is drawn from its data/village/buildings document. Building tier is
visual (plot -> tier1 tint) and functional (services/NPCs arrive in later
phases). Interacting (INTERACT/F) with a building attempts its next upgrade
and reports the result on screen.

Greybox scope (RULES.md §0): tinted rects, neutral names, no lore.
"""

from __future__ import annotations

from core.content_registry import ContentRegistry
from core.enums import SceneID
from engine.scene import Scene
from gameplay.player.aim_controller import AimController
from gameplay.player.player import Player
from gameplay.player.player_controller import PlayerController
from gameplay.village.building import Building
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
_WALL_COLOR: Color = (80, 80, 96)
_PLOT_COLOR: Color = (70, 70, 80)
_TIER1_COLOR: Color = (70, 130, 200)
_BUILDING_FRAME: Color = (20, 20, 28)
_TEXT_COLOR: Color = (230, 230, 235)
_HINT_COLOR: Color = (170, 200, 170)
_MSG_OK: Color = (110, 220, 110)
_MSG_ERR: Color = (230, 110, 110)
_PLAYER_COLOR: Color = (150, 195, 250)
_DUNGEON_DOOR_COLOR: Color = (120, 70, 60)

# Building visual tiers -> tint (greybox only, not a content decision).
_TIER_TINTS: dict[str, Color] = {
    "plot": _PLOT_COLOR,
    "tier1": _TIER1_COLOR,
}


class VillageScene(Scene):
    """Walkable village hub with tiered building plots."""

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

        if Action.INTERACT in frame.pressed and self._hovered_building is not None:
            self._try_upgrade(self._hovered_building)

        if self._try_enter_dungeon():
            self._message = "Dungeon entrance (run start — Phase 15)"
            self._message_is_error = False

        if self._message_timer > 0.0:
            self._message_timer -= dt
            if self._message_timer <= 0.0:
                self._message = ""

        self.camera.follow(self.player.body.x, self.player.body.y, dt)

    # -- Render --

    def render(self, renderer: Renderer) -> None:
        renderer.draw_rect(self.camera.screen_rect(self.room.bounds), _GRASS_COLOR)
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
            screen_rect = self.camera.screen_rect(AABB(bx, by, bw, bh))
            tint = _TIER_TINTS.get(building.visual_state, _PLOT_COLOR)
            # Hovered building gets a brighter frame.
            if building is self._hovered_building:
                renderer.draw_rect(screen_rect, (255, 255, 255))
                inner = (screen_rect[0] + 3, screen_rect[1] + 3,
                         screen_rect[2] - 6, screen_rect[3] - 6)
                renderer.draw_rect(inner, tint)
            else:
                renderer.draw_rect(screen_rect, tint)
                inner = (screen_rect[0] + 2, screen_rect[1] + 2,
                         screen_rect[2] - 4, screen_rect[3] - 4)
                renderer.draw_rect(inner, _BUILDING_FRAME)
            # Building name + tier.
            label = f"{building.name}  T{building.current_tier + 1}"
            sx, sy = self.camera.world_to_screen(bx + 8, by + 8)
            renderer.draw_text(label, int(sx), int(sy), _TEXT_COLOR, 14)

        # Player.
        body_rect = self.camera.screen_rect(self.player.body.box)
        renderer.draw_rect(body_rect, _PLAYER_COLOR)

        # HUD: village resources + town level.
        w, h = renderer.size
        gold = self.village.resources.get(GOLD, 0)
        relics = self.village.resources.get(RELIC, 0)
        renderer.draw_text(
            f"Town Lv {self.village.town_level}    Gold {gold}    Relics {relics}",
            20, 20, _TEXT_COLOR, 16,
        )
        renderer.draw_text(
            "WASD move  |  F: interact (upgrade building)",
            20, h - 34, _HINT_COLOR, 13,
        )
        renderer.draw_text(
            "Walk to the bottom-center door to enter the dungeon",
            20, h - 18, _HINT_COLOR, 12,
        )

        if self._hovered_building is not None:
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
            renderer.draw_text(self._message, w // 2 - 160, h // 2, color, 16)
