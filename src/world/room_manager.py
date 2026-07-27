"""Room manager: tracks the current room and handles room transitions.

Phase 6 establishes the core room-transition infrastructure:
  - RoomManager holds the current Room and its connected neighbours.
  - It loads new rooms from the ContentRegistry.
  - It detects when the player overlaps a door and triggers a transition.
  - Callbacks allow the scene to react (reposition enemies, reset camera, etc.).

The manager does NOT own the player or camera — the scene does.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from core.content_registry import ContentRegistry
from physics.collision import AABB, CollisionWorld
from world.room import Door, Room

# Callback type: (new_room, spawn_x, spawn_y) -> None
TransitionCallback = Callable[[Room, float, float], None]


@dataclass
class RoomManager:
    """Manages the current room, loads neighbours, handles transitions.

    Usage:
        manager = RoomManager(registry)
        manager.load_room("greybox_arena")
        # Each frame:
        door = manager.check_transition(player_box)
        if door:
            manager.transition(door.target_room, door.target_spawn)
    """

    registry: ContentRegistry
    current_room: Room | None = None
    _on_transition: TransitionCallback | None = None

    def on_transition(self, callback: TransitionCallback) -> None:
        """Register a callback fired after each room transition.

        The scene uses this to reposition the player, camera, and enemies.
        """
        self._on_transition = callback

    def load_room(self, room_id: str) -> Room:
        """Load a room by id from the registry, build its collision world.

        Returns the loaded Room (also sets current_room).
        """
        document: dict[str, Any] = self.registry.get("world", room_id)
        room = Room.from_document(document)
        self.current_room = room
        return room

    def build_world(self, room: Room | None = None) -> CollisionWorld:
        """Build a CollisionWorld from a room's solids."""
        target = room or self.current_room
        if target is None:
            raise RuntimeError("No room loaded")
        return target.build_collision_world()

    def check_transition(self, player_box: AABB) -> Door | None:
        """Check if the player overlaps any door in the current room.

        Returns the Door being triggered, or None.
        """
        if self.current_room is None:
            return None
        for door in self.current_room.doors:
            if player_box.intersects(door.box):
                return door
        return None

    def transition(self, door: Door) -> Room:
        """Execute a room transition: load the target room and fire callback.

        Returns the new Room.
        """
        new_room = self.load_room(door.target_room)
        if self._on_transition is not None:
            spawn_x, spawn_y = door.target_spawn
            self._on_transition(new_room, spawn_x, spawn_y)
        return new_room
