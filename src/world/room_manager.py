"""Room manager: tracks the current room and handles room transitions.

Phase 6 establishes the core room-transition infrastructure:
  - RoomManager holds the current Room and its connected neighbours.
  - It loads new rooms from the ContentRegistry or from a pre-assembled floor.
  - It detects when the player overlaps a door and triggers a transition.
  - Callbacks allow the scene to react (reposition enemies, reset camera, etc.).

The manager does NOT own the player or camera — the scene does.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from core.content_registry import ContentRegistry
from physics.collision import AABB, CollisionWorld
from world.floor_assembler import FloorData
from world.room import Door, Room

# Callback type: (new_room, spawn_x, spawn_y) -> None
TransitionCallback = Callable[[Room, float, float], None]


@dataclass
class RoomManager:
    """Manages the current room, loads neighbours, handles transitions.

    Two modes:
      1. Registry mode: load_room(room_id) loads from ContentRegistry.
      2. Floor mode: load_floor(floor_data) uses pre-assembled rooms.

    In floor mode, all rooms are pre-loaded and transitions look up
    the target room from the floor data.
    """

    registry: ContentRegistry | None = None
    current_room: Room | None = None
    _on_transition: TransitionCallback | None = None

    # Floor mode state.
    _floor_data: FloorData | None = None
    _rooms: dict[str, Room] = field(default_factory=dict)

    def on_transition(self, callback: TransitionCallback) -> None:
        """Register a callback fired after each room transition.

        The scene uses this to reposition the player, camera, and enemies.
        """
        self._on_transition = callback

    def load_floor(self, floor_data: FloorData) -> Room:
        """Load a pre-assembled floor and return the start room."""
        self._floor_data = floor_data
        self._rooms = dict(floor_data.rooms)
        self.current_room = self._rooms[floor_data.start_room_id]
        return self.current_room

    def load_room(self, room_id: str) -> Room:
        """Load a room by id from the registry or floor data."""
        if room_id in self._rooms:
            room = self._rooms[room_id]
        elif self.registry is not None:
            document: dict[str, Any] = self.registry.get("world", room_id)
            room = Room.from_document(document)
        else:
            raise RuntimeError(
                f"Cannot load room '{room_id}': not in floor data and no registry"
            )
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

    @property
    def current_room_id(self) -> str | None:
        """The id of the current room, or None."""
        if self.current_room is None:
            return None
        return self.current_room.room_id
