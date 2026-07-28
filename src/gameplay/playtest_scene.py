"""
Playtest scene: greybox vertical slice with full run lifecycle,
encounter system, rewards, boss, and restart.

Phase 8 integrates:
  - Run lifecycle (RunManager)
  - Room encounter (clear detection, door locking)
  - Reward system (3-choice, data-driven buffs)
  - Boss detection
  - Death/victory states with restart
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
from gameplay.combat.encounter import RoomEncounter
from gameplay.enemies.enemy import Enemy
from gameplay.enemies.enemy_ai import SimpleAI
from gameplay.enemies.enemy_factory import build_enemy
from gameplay.player.aim_controller import AimController
from gameplay.player.player import Player
from gameplay.player.player_controller import PlayerController
from gameplay.player.player_state import PlayerState
from gameplay.roguelike.rewards import apply_reward, get_random_rewards
from gameplay.roguelike.run import RunManager
from input.input_manager import Action, ActionFrame
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
_HEALTH_BAR_WIDTH = 24.0
_HEALTH_BAR_HEIGHT = 3.0
_HEALTH_BAR_ENEMY_Y_OFFSET = 20.0
_OVERLAY_BG: Color = (0, 0, 0)
_TEXT_COLOR: Color = (230, 230, 230)

_STATE_COLORS: dict[PlayerState, Color] = {
    PlayerState.IDLE: (190, 190, 215),
    PlayerState.MOVE: (150, 195, 250),
    PlayerState.DODGE: (250, 225, 130),
    PlayerState.HIT: (245, 120, 120),
    PlayerState.DEAD: (90, 90, 90),
}
_INVULNERABLE_TINT: Color = (255, 255, 255)
_YELLOW: Color = (255, 200, 50)
_REWARD_COLORS: list[Color] = [
    (200, 80, 80),
    (80, 160, 200),
    (80, 200, 100),
]


def _fallback_enemy_spawns(room: Room) -> list[tuple[float, float]]:
    cx, cy = room.width / 2.0, room.height / 2.0
    return [
        (cx + 160.0, cy - 60.0),
        (cx + 160.0, cy + 60.0),
        (cx + 260.0, cy),
    ]


class PlaytestScene(Scene):
    """Greybox vertical slice: full run lifecycle, combat, rewards, boss, restart."""

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

        self._stage_manager = stage_manager
        if stage_manager is not None:
            stage_manager.on_transition(self._on_room_transition)
            stage_manager.on_stage_complete(self._on_stage_complete)

        self._run = RunManager()
        self._encounter: RoomEncounter = RoomEncounter()
        self._reward_options: list = []
        self._reward_pending = False

    @property
    def enemies(self) -> tuple[tuple[Enemy, SimpleAI], ...]:
        return tuple(self._enemies)

    # -- Transitions --

    def _on_room_transition(self, new_room: Room, sx: float, sy: float) -> None:
        self.room = new_room
        self.world = new_room.build_collision_world()
        self.player.body.teleport(sx, sy)
        self.camera.center_on(sx, sy)
        self.camera.set_bounds(self.room.bounds)
        self._spawn_room_enemies()
        self._encounter = RoomEncounter()
        self._reward_pending = False

        # Boss floor detection.
        if new_room.kind == "boss":
            self._run.start_boss()

    def _on_stage_complete(self) -> None:
        self.stage_completed = True
        _logger.info("Stage complete!")

    def _spawn_room_enemies(self) -> None:
        self._enemies.clear()
        if self._registry is None or self._stage_manager is None:
            return
        encounter = self._stage_manager.current_floor.encounters.get(
            self.room.room_id, ()
        )
        if not encounter:
            return
        spawns = list(self.room.enemy_spawns) or _fallback_enemy_spawns(self.room)
        idx = 0
        for eid, count in encounter:
            for _ in range(count):
                x, y = spawns[idx % len(spawns)]
                self._enemies.append(build_enemy(self._registry, eid, x=x, y=y))
                idx += 1
        self._encounter.activate(len(self._enemies))

    def _restart_run(self) -> None:
        self.player.reset()
        self._run.reset()
        self._run.start()
        if self._stage_manager is not None:
            self._stage_manager.start()
            start = self._stage_manager.current_room
            if start is not None:
                self.room = start
                self.world = start.build_collision_world()
                self.player.body.teleport(*start.player_spawn)
                self.camera.center_on(*start.player_spawn)
                self.camera.set_bounds(self.room.bounds)
                self._spawn_room_enemies()
        self._encounter = RoomEncounter()
        self._reward_options = []
        self._reward_pending = False
        self.stage_completed = False

    def _handle_reward_selection(self, frame: ActionFrame) -> None:
        """Select reward based on keyboard aim direction (1/2/3)."""
        if not self._reward_options:
            self._reward_pending = False
            return
        idx = -1
        if frame.aim_x > 0.5:
            idx = 0
        elif frame.aim_x < -0.5:
            idx = 2
        elif frame.aim_y > 0.5 or frame.aim_y < -0.5:
            idx = 1
        if idx >= 0 and idx < len(self._reward_options):
            apply_reward(self._reward_options[idx], self.player)
            self._run.state.rewards_collected.append(self._reward_options[idx].id)
            self._reward_options = []
            self._reward_pending = False

    # -- Main update --

    def update(self, frame: ActionFrame, dt: float) -> None:
        # Restart on game-over.
        if self._run.ended:
            if Action.PRIMARY_ATTACK in frame.pressed:
                self._restart_run()
            return

        # Reward selection paused state.
        if self._reward_pending:
            self._handle_reward_selection(frame)
            return

        aim = self._aim.resolve(frame, self.player.body.x, self.player.body.y)
        self.player.set_aim(aim.direction[0], aim.direction[1])
        intent = self._controller.build_intent(frame)
        self.player.update(intent, self.world, dt)

        for enemy, ai in self._enemies:
            if not enemy.alive:
                continue
            ai.update(self.player.body.x, self.player.body.y, dt)
            enemy.update(dt)
            enemy.integrate(dt)

        # -- Hitboxes --
        player_hitboxes: list[tuple[str, AABB, DamageInstance]] = []
        if self.player.attack_executor.hitbox_active():
            ax, ay = self.player.aim_vector
            hb = self.player.attack_executor.hitbox_for(
                self.player.body.x,
                self.player.body.y,
                facing_x=ax,
                facing_y=ay,
            )
            if hb is not None:
                player_hitboxes.append(
                    (
                        "player",
                        hb,
                        DamageInstance(
                            value=self.player.attack_executor.data.damage,
                            types=self.player.attack_executor.data.damage_types,
                            source_layer=self.player.attack_executor.data.layer,
                        ),
                    )
                )

        enemy_hitboxes: list[tuple[str, AABB, DamageInstance]] = []
        for enemy, _ai in self._enemies:
            if not enemy.alive:
                continue
            ha = enemy.hitbox_aabb
            if ha is not None:
                enemy_hitboxes.append(
                    (
                        enemy.entity.name,
                        ha,
                        DamageInstance(
                            value=enemy.attack_executor.data.damage,
                            types=enemy.attack_executor.data.damage_types,
                            source_layer=enemy.attack_executor.data.layer,
                        ),
                    )
                )

        # Resolve hits.
        if player_hitboxes:
            ents = [
                CombatEntity(
                    id=e.entity.name,
                    body_x=e.body.x,
                    body_y=e.body.y,
                    hurtbox_aabb=e.hurtbox.box_at(e.body.x, e.body.y),
                    vulnerable=e.alive,
                    damage_target=e,
                    invuln_service=e.invuln_service,
                )
                for e, _ in self._enemies
                if e.alive
            ]
            hits = self._combat.resolve_hits(player_hitboxes, ents)
            for hit in hits:
                if hit.result.killed:
                    self._encounter.on_enemy_died()
                    self._run.on_enemy_kill()

        if enemy_hitboxes and self.player.alive:
            pe = [
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
            hits = self._combat.resolve_hits(enemy_hitboxes, pe)
            for hit in hits:
                if hit.result.dealt > 0:
                    self.player.set_hitstun(0.15)
                    self.player.on_hit(0.15)
                    if self.player.health <= 0.0:
                        self.player.die()
                        self._run.on_death()

        # Room cleared → reward.
        if self._encounter.cleared and not self._reward_pending:
            self._run.on_room_clear()
            self._reward_options = get_random_rewards(3)
            self._reward_pending = True

        # Player died (state check).
        if self.player.state is PlayerState.DEAD and not self._run.ended:
            self._run.on_death()

        # Stage complete check.
        if self.stage_completed:
            self._run.on_victory()

        # Room transition.
        if self._stage_manager is not None and not self._reward_pending:
            door = self._stage_manager.check_transition(self.player.body.box)
            if door is not None:
                self._stage_manager.transition(door)

        self.camera.follow(self.player.body.x, self.player.body.y, dt)

    # -- Rendering --

    def render(self, renderer: Renderer) -> None:
        renderer.draw_rect(self.camera.screen_rect(self.room.bounds), _FLOOR_COLOR)
        for solid in self.room.solids:
            renderer.draw_rect(self.camera.screen_rect(solid), _WALL_COLOR)

        for enemy, _ai in self._enemies:
            if not enemy.alive:
                continue
            renderer.draw_rect(self.camera.screen_rect(enemy.body.box), _ENEMY_COLOR)
            ha = enemy.hurtbox.box_at(enemy.body.x, enemy.body.y)
            renderer.draw_rect(self.camera.screen_rect(ha), _ENEMY_HURTBOX_ALPHA)
            ratio = enemy.health / enemy.config.max_health
            bx = enemy.body.x - _HEALTH_BAR_WIDTH / 2.0
            by = enemy.body.y - _HEALTH_BAR_ENEMY_Y_OFFSET
            bg = AABB(bx, by, _HEALTH_BAR_WIDTH, _HEALTH_BAR_HEIGHT)
            renderer.draw_rect(self.camera.screen_rect(bg), _HEALTH_BAR_BG)
            if ratio > 0.0:
                fg = AABB(bx, by, _HEALTH_BAR_WIDTH * ratio, _HEALTH_BAR_HEIGHT)
                renderer.draw_rect(self.camera.screen_rect(fg), _HEALTH_BAR_FG)
            eha = enemy.hitbox_aabb
            if eha is not None:
                renderer.draw_rect(self.camera.screen_rect(eha), _ENEMY_ATTACK_COLOR)

        pose = self.player.animation_pose
        color = _STATE_COLORS[pose.state]
        if self.player.invulnerable:
            color = _INVULNERABLE_TINT
        renderer.draw_rect(self.camera.screen_rect(self.player.body.box), color)

        if self.player.attack_executor.hitbox_active():
            ax, ay = self.player.aim_vector
            hb = self.player.attack_executor.hitbox_for(
                self.player.body.x,
                self.player.body.y,
                facing_x=ax,
                facing_y=ay,
            )
            if hb is not None:
                renderer.draw_rect(self.camera.screen_rect(hb), _ATTACK_HITBOX_COLOR)

        fx, fy = pose.facing.vector
        marker = AABB(
            self.player.body.x
            + fx * _FACING_MARKER_DISTANCE
            - _FACING_MARKER_SIZE / 2.0,
            self.player.body.y
            + fy * _FACING_MARKER_DISTANCE
            - _FACING_MARKER_SIZE / 2.0,
            _FACING_MARKER_SIZE,
            _FACING_MARKER_SIZE,
        )
        renderer.draw_rect(self.camera.screen_rect(marker), _FACING_COLOR)

        # Reward overlay.
        if self._reward_pending and self._reward_options:
            for i, rew in enumerate(self._reward_options):
                rx = 40 + i * 120
                ry = 60
                rw, rh = 100, 40
                renderer.draw_rect((rx, ry, rw, rh), _REWARD_COLORS[i % 3])
                renderer.draw_rect((rx + 2, ry + 2, rw - 4, rh - 4), (30, 30, 30))

        # Game-over overlay (full-screen dark overlay, no text renderer yet).
        if self._run.ended:
            w, h = renderer.size
            renderer.draw_rect((0, 0, w, h), (0, 0, 0))
