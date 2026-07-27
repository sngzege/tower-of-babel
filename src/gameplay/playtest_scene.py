"""Greybox playtest scene: the Phase 3 playable slice with Phase 4 combat hooks
and Phase 5 enemy integration.

One hand-authored room, the real player, one or more greybox enemies, and the
follow camera — all wired from data files. This scene exists to evaluate game
feel (Phase 3 spec: greybox test map); the real dungeon scene replaces it when
rooms/doors arrive (Phase 6+), reusing Player, Room, CollisionWorld, and Camera
unchanged.

Phase 4+5 additions:
  - CombatSystem for hit resolution (player attacks enemies, enemies attack player)
  - Greybox enemy entities with AI (chase + attack)
  - Attack hitbox visualisation during the active window
  - Enemy rendering (tinted rect + health bar)
  - Invulnerability-aware rendering
  - Player hitstun and death handling
"""

from __future__ import annotations

from core.enums import SceneID
from engine.scene import Scene
from gameplay.combat.combat_system import (
    CombatEntity,
    CombatSystem,
)
from gameplay.combat.damage import DamageInstance
from gameplay.enemies.enemy import Enemy
from gameplay.enemies.enemy_ai import SimpleAI
from gameplay.player.aim_controller import AimController
from gameplay.player.player import Player
from gameplay.player.player_controller import PlayerController
from gameplay.player.player_state import PlayerState
from input.input_manager import ActionFrame
from physics.collision import AABB, CollisionWorld
from rendering.camera import Camera
from rendering.renderer import Color, Renderer
from world.room import Room

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


class PlaytestScene(Scene):
    """Playable greybox room: move, dodge, collide, camera follow, aim, attack."""

    scene_id = SceneID.DUNGEON

    def __init__(
        self,
        player: Player,
        room: Room,
        world: CollisionWorld,
        camera: Camera,
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
        self._enemies: list[tuple[Enemy, SimpleAI]] = enemies or []

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
                    # Player took damage → apply hitstun (if not mid-dodge).
                    self.player.set_hitstun(0.15)
                    self.player.on_hit(0.15)
                    if self.player.health <= 0.0:
                        self.player.die()

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
            # Enemy hurtbox outline.
            hurtbox_aabb = enemy.hurtbox.box_at(enemy.body.x, enemy.body.y)
            renderer.draw_rect(
                self.camera.screen_rect(hurtbox_aabb),
                _ENEMY_HURTBOX_ALPHA,
            )
            # Enemy health bar.
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

            # Enemy attack hitbox.
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

        # Player attack hitbox (uses raw 360° aim_vector).
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
