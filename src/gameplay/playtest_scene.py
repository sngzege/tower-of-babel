"""Greybox playtest scene: the Phase 3 playable slice.

One hand-authored room, the real player, and the follow camera - all wired
from data files. This scene exists to evaluate game feel (Phase 3 spec:
greybox test map); the real dungeon scene replaces it when rooms/doors
arrive (Phase 6+), reusing Player, Room, CollisionWorld, and Camera
unchanged. Rendering is placeholder tinting driven by the animation hook;
the sprite pipeline (later phase) swaps it without touching gameplay.

The scene owns the ``AimController`` (priority policy between mouse and
keyboard aim) and injects the resolved aim vector into the Player each
frame. This keeps the Player rendering-agnostic (AimController does depend
on Camera's ``screen_to_world``, which is rendering, so the scene bridges
the boundary per the dependency rules).
"""

from __future__ import annotations

from core.enums import SceneID
from engine.scene import Scene
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

_STATE_COLORS: dict[PlayerState, Color] = {
    PlayerState.IDLE: (190, 190, 215),
    PlayerState.MOVE: (150, 195, 250),
    PlayerState.DODGE: (250, 225, 130),
    PlayerState.HIT: (245, 120, 120),
    PlayerState.DEAD: (90, 90, 90),
}
_INVULNERABLE_TINT: Color = (255, 255, 255)


class PlaytestScene(Scene):
    """Playable greybox room: move, dodge, collide, camera follow, aim."""

    scene_id = SceneID.DUNGEON

    def __init__(
        self,
        player: Player,
        room: Room,
        world: CollisionWorld,
        camera: Camera,
        controller: PlayerController | None = None,
    ) -> None:
        self.player = player
        self.room = room
        self.world = world
        self.camera = camera
        self._controller = controller or PlayerController()
        self._aim = AimController(screen_to_world=camera.screen_to_world)

    def enter(self) -> None:
        spawn_x, spawn_y = self.room.player_spawn
        self.player.body.teleport(spawn_x, spawn_y)
        self.camera.center_on(spawn_x, spawn_y)

    def update(self, frame: ActionFrame, dt: float) -> None:
        aim = self._aim.resolve(frame, self.player.body.x, self.player.body.y)
        self.player.set_aim(aim.direction[0], aim.direction[1])
        intent = self._controller.build_intent(frame)
        self.player.update(intent, self.world, dt)
        self.camera.follow(self.player.body.x, self.player.body.y, dt)

    def render(self, renderer: Renderer) -> None:
        renderer.draw_rect(self.camera.screen_rect(self.room.bounds), _FLOOR_COLOR)
        for solid in self.room.solids:
            renderer.draw_rect(self.camera.screen_rect(solid), _WALL_COLOR)

        pose = self.player.animation_pose
        color = _STATE_COLORS[pose.state]
        if self.player.invulnerable:
            color = _INVULNERABLE_TINT
        renderer.draw_rect(self.camera.screen_rect(self.player.body.box), color)

        facing_x, facing_y = pose.facing.vector
        marker = AABB(
            self.player.body.x + facing_x * _FACING_MARKER_DISTANCE
            - _FACING_MARKER_SIZE / 2.0,
            self.player.body.y + facing_y * _FACING_MARKER_DISTANCE
            - _FACING_MARKER_SIZE / 2.0,
            _FACING_MARKER_SIZE,
            _FACING_MARKER_SIZE,
        )
        renderer.draw_rect(self.camera.screen_rect(marker), _FACING_COLOR)
