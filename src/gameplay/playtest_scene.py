"""Greybox playtest scene: greybox playable slice with combat and
Phase 7 multi-floor stage traversal.

Supports both single-room mode (legacy) and stage mode.
In stage mode, the scene is driven by a StageManager: the player traverses
the connected rooms of each floor, and floor exits advance to the next
floor until the stage is complete. Enemy population comes from the
assembled floor data (encounters + template spawn points), not hardcoded.
"""

from __future__ import annotations

from core.content_registry import ContentRegistry
from core.enums import SceneID
from engine.scene import Scene
from gameplay.combat.combat_system import (
    CombatEntity,
    CombatSystem,
)
from gameplay.combat.damage import DamageInstance
from gameplay.enemies.enemy import Enemy
from gameplay.enemies.enemy_ai import SimpleAI
from gameplay.enemies.enemy_factory import build_enemy
from gameplay.player.aim_controller import AimController
from gameplay.player.player import Player
from gameplay.player.player_controller import PlayerController
from gameplay.player.player_state import PlayerState
from input.input_manager import ActionFrame
from physics.collision import AABB, CollisionWorld
from rendering.camera import Camera
from rendering.renderer import Color, Renderer
from utils.logger import get_logger
from world.room import Room
from world.stage_manager import StageManager

_logger = get_logger(__name__)

_FLOOR_COLOR: Color = (34, 34, 40)
_WALL_COLOR: Color = (92, 92, 112)
_FACING_COLOR: Color = (245, 245, 245)
_FACING_MARKER_SIZE = 6.0
_FACING_MARKER_DISTANCE = 12.0
_ATTACK_HITBOX_COLOR: Color = (255, 120, 50)
_ENEMY_COLOR: Color = (200, 60, 60)
_ENEMY_ATTACK_COLOR: Color = (255, 80, 80)
_ENEMY_HURTBOX_ALPHA: Color = (200, 60, 60)
_HEALTH_BAR_BG: Color = (50, 50, 50)
_HEALTH_BAR_FG: Color = (80, 200, 80)
_HEALTH_BAR_ENEMY_Y_OFFSET = 20.0
_HEALTH_BAR_WIDTH = 24.0
_HEALTH_BAR_HEIGHT = 3.0

_STATE_COLORS: dict[PlayerState, Color] = {
    PlayerState.IDLE: (190, 190, 215),
    PlayerState.MOVE: (150, 195, 250),
    PlayerState.DODGE: (250, 225, 130),
    PlayerState.HIT: (245, 120, 120),
    PlayerState.DEAD: (90, 90, 90),
}
_INVULNERABLE_TINT: Color = (255, 255, 255)


def _fallback_enemy_spawns(room: Room) -> list[tuple[float, float]]:
    """Default enemy spawn points when a template defines none.

    A small deterministic ring right of the room center; used only when a
    room with an encounter has no explicit ``enemy_spawns``.
    """
    center_x = room.width / 2.0
    center_y = room.height / 2.0
    return [
        (center_x + 160.0, center_y - 60.0),
        (center_x + 160.0, center_y + 60.0),
        (center_x + 260.0, center_y),
    ]


class PlaytestScene(Scene):
    """Playable greybox room: move, dodge, collide, camera follow, aim, attack."""

    scene_id = SceneID.DUNGEON

    def __init__(
        self,
        player: Player,
        room: Room,
        world: CollisionWorld,
        camera: Camera,
        registry: ContentRegistry | None = None,
        stage_manager: StageManager | None = None,
        enemies: list[tuple[Enemy, SimpleAI]] | None = None,
        controller: PlayerController | None = None,
    ) -> None:
        self.player = player
        self.room = room
        self.world = world
        self.camera = camera
        self._controller = controller or PlayerController()
        self._aim = AimController(screen_to_world=camera.screen_to_world)
        self._combat = CombatSystem(events=None)
        self._registry = registry
        self._enemies: list[tuple[Enemy, SimpleAI]] = enemies or []
        self.stage_completed = False

        # Phase 7: Stage manager for room/floor transitions.
        self._stage_manager = stage_manager
        if stage_manager is not None:
            stage_manager.on_transition(self._on_room_transition)
            stage_manager.on_stage_complete(self._on_stage_complete)

    @property
    def enemies(self) -> tuple[tuple[Enemy, SimpleAI], ...]:
        """The enemies currently populating the room (read-only view)."""
        return tuple(self._enemies)

    # -- Room/floor transition callbacks --

    def _on_room_transition(
        self, new_room: Room, spawn_x: float, spawn_y: float
    ) -> None:
        """Callback fired when the player walks through a door or floor exit."""
        self.room = new_room
        self.world = new_room.build_collision_world()
        self.player.body.teleport(spawn_x, spawn_y)
        self.camera.center_on(spawn_x, spawn_y)
        self.camera.set_bounds(self.room.bounds)

        # Spawn enemies for the new room from the floor's encounter data.
        self._spawn_room_enemies()

    def _on_stage_complete(self) -> None:
        """Callback fired once when the final floor exit is reached."""
        self.stage_completed = True
        _logger.info("Stage complete — the greybox stage exit was reached")

    def _spawn_room_enemies(self) -> None:
        """Populate the current room from its assembled encounter data."""
        self._enemies.clear()

        if self._registry is None or self._stage_manager is None:
            return

        encounter = self._stage_manager.current_floor.encounters.get(
            self.room.room_id, ()
        )
        if not encounter:
            return

        spawn_points = list(self.room.enemy_spawns) or _fallback_enemy_spawns(self.room)
        index = 0
        for enemy_id, count in encounter:
            for _ in range(count):
                x, y = spawn_points[index % len(spawn_points)]
                self._enemies.append(
                    build_enemy(self._registry, enemy_id, x=x, y=y)
                )
                index += 1

    # -- Lifecycle --

    def enter(self) -> None:
        spawn_x, spawn_y = self.room.player_spawn
        self.player.body.teleport(spawn_x, spawn_y)
        self.camera.center_on(spawn_x, spawn_y)

    def update(self, frame: ActionFrame, dt: float) -> None:
        aim = self._aim.resolve(frame, self.player.body.x, self.player.body.y)
        self.player.set_aim(aim.direction[0], aim.direction[1])
        intent = self._controller.build_intent(frame)
        self.player.update(intent, self.world, dt)

        # Update enemies (AI + combat timers + movement).
        for enemy, ai in self._enemies:
            if not enemy.alive:
                continue
            ai.update(self.player.body.x, self.player.body.y, dt)
            enemy.update(dt)
            enemy.integrate(dt)

        # -- Hit resolution --
        # Player attack hitboxes.
        player_hitboxes: list[tuple[str, AABB, DamageInstance]] = []
        if self.player.attack_executor.hitbox_active():
            aim_x, aim_y = self.player.aim_vector
            hb_aabb = self.player.attack_executor.hitbox_for(
                self.player.body.x,
                self.player.body.y,
                facing_x=aim_x,
                facing_y=aim_y,
            )
            if hb_aabb is not None:
                player_hitboxes.append(
                    (
                        "player",
                        hb_aabb,
                        DamageInstance(
                            value=self.player.attack_executor.data.damage,
                            types=self.player.attack_executor.data.damage_types,
                            source_layer=self.player.attack_executor.data.layer,
                        ),
                    )
                )

        # Enemy attack hitboxes.
        enemy_hitboxes: list[tuple[str, AABB, DamageInstance]] = []
        for enemy, _ai in self._enemies:
            if not enemy.alive:
                continue
            hitbox_aabb = enemy.hitbox_aabb
            if hitbox_aabb is not None:
                enemy_hitboxes.append(
                    (
                        enemy.entity.name,
                        hitbox_aabb,
                        DamageInstance(
                            value=enemy.attack_executor.data.damage,
                            types=enemy.attack_executor.data.damage_types,
                            source_layer=enemy.attack_executor.data.layer,
                        ),
                    )
                )

        # Resolve player attacks → enemies.
        if player_hitboxes:
            enemy_entities = [
                CombatEntity(
                    id=enemy.entity.name,
                    body_x=enemy.body.x,
                    body_y=enemy.body.y,
                    hurtbox_aabb=enemy.hurtbox.box_at(enemy.body.x, enemy.body.y),
                    vulnerable=enemy.alive,
                    damage_target=enemy,
                    invuln_service=enemy.invuln_service,
                )
                for enemy, _ai in self._enemies
                if enemy.alive
            ]
            self._combat.resolve_hits(player_hitboxes, enemy_entities)

        # Resolve enemy attacks → player.
        if enemy_hitboxes and self.player.alive:
            player_entity = [
                CombatEntity(
                    id="player",
                    body_x=self.player.body.x,
                    body_y=self.player.body.y,
                    hurtbox_aabb=self.player.hurtbox.box_at(
                        self.player.body.x, self.player.body.y
                    ),
                    vulnerable=self.player.alive,
                    damage_target=self.player,
                    invuln_service=self.player.invuln_service,
                )
            ]
            hits = self._combat.resolve_hits(enemy_hitboxes, player_entity)
            for hit in hits:
                if hit.result.dealt > 0:
                    self.player.set_hitstun(0.15)
                    self.player.on_hit(0.15)
                    if self.player.health <= 0.0:
                        self.player.die()

        # Check room/floor transition.
        if self._stage_manager is not None:
            door = self._stage_manager.check_transition(self.player.body.box)
            if door is not None:
                self._stage_manager.transition(door)

        self.camera.follow(self.player.body.x, self.player.body.y, dt)

    # -- Rendering --

    def render(self, renderer: Renderer) -> None:
        renderer.draw_rect(self.camera.screen_rect(self.room.bounds), _FLOOR_COLOR)
        for solid in self.room.solids:
            renderer.draw_rect(self.camera.screen_rect(solid), _WALL_COLOR)

        # Render enemies.
        for enemy, _ai in self._enemies:
            if not enemy.alive:
                continue
            color = _ENEMY_COLOR
            renderer.draw_rect(
                self.camera.screen_rect(enemy.body.box), color
            )
            hurtbox_aabb = enemy.hurtbox.box_at(enemy.body.x, enemy.body.y)
            renderer.draw_rect(
                self.camera.screen_rect(hurtbox_aabb),
                _ENEMY_HURTBOX_ALPHA,
            )
            health_ratio = enemy.health / enemy.config.max_health
            bar_x = enemy.body.x - _HEALTH_BAR_WIDTH / 2.0
            bar_y = enemy.body.y - _HEALTH_BAR_ENEMY_Y_OFFSET
            bg_rect = AABB(bar_x, bar_y, _HEALTH_BAR_WIDTH, _HEALTH_BAR_HEIGHT)
            renderer.draw_rect(self.camera.screen_rect(bg_rect), _HEALTH_BAR_BG)
            if health_ratio > 0.0:
                fg_rect = AABB(
                    bar_x, bar_y,
                    _HEALTH_BAR_WIDTH * health_ratio,
                    _HEALTH_BAR_HEIGHT,
                )
                renderer.draw_rect(
                    self.camera.screen_rect(fg_rect), _HEALTH_BAR_FG
                )

            hitbox_aabb = enemy.hitbox_aabb
            if hitbox_aabb is not None:
                renderer.draw_rect(
                    self.camera.screen_rect(hitbox_aabb), _ENEMY_ATTACK_COLOR
                )

        # Render player.
        pose = self.player.animation_pose
        color = _STATE_COLORS[pose.state]
        if self.player.invulnerable:
            color = _INVULNERABLE_TINT
        renderer.draw_rect(self.camera.screen_rect(self.player.body.box), color)

        # Player attack hitbox (raw 360° aim_vector).
        if self.player.attack_executor.hitbox_active():
            aim_x, aim_y = self.player.aim_vector
            hitbox_aabb = self.player.attack_executor.hitbox_for(
                self.player.body.x,
                self.player.body.y,
                facing_x=aim_x,
                facing_y=aim_y,
            )
            if hitbox_aabb is not None:
                renderer.draw_rect(
                    self.camera.screen_rect(hitbox_aabb), _ATTACK_HITBOX_COLOR
                )

        # Facing direction marker.
        facing_x, facing_y = pose.facing.vector
        marker = AABB(
            self.player.body.x
            + facing_x * _FACING_MARKER_DISTANCE
            - _FACING_MARKER_SIZE / 2.0,
            self.player.body.y
            + facing_y * _FACING_MARKER_DISTANCE
            - _FACING_MARKER_SIZE / 2.0,
            _FACING_MARKER_SIZE,
            _FACING_MARKER_SIZE,
        )
        renderer.draw_rect(self.camera.screen_rect(marker), _FACING_COLOR)
