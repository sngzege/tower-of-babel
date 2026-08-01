"""Stage manager: multi-floor stage traversal (Phase 7).

Owns the assembled StageData and drives both transition levels:
  - Room → room inside the current floor (delegated to RoomManager).
  - Floor → floor when the player walks through the floor-exit door
    (a door whose target is FLOOR_EXIT_TARGET). On the last floor the
    exit completes the stage instead (greybox stage exit; later this
    connects to the boss/stage-completion flow).

The manager does NOT own the player or camera — the scene reacts through
callbacks, exactly as with RoomManager.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from physics.collision import AABB
from world.floor_assembler import FLOOR_EXIT_TARGET, FloorData
from world.room import Door, Room
from world.room_manager import RoomManager
from world.stage import StageData

# Callback type: (new_room, spawn_x, spawn_y) -> None
TransitionCallback = Callable[[Room, float, float], None]
# Callback fired once when the final floor exit is reached.
StageCompleteCallback = Callable[[], None]


@dataclass
class StageManager:
    """Tracks the current floor/room and handles all stage transitions."""

    stage_data: StageData
    floor_index: int = 0
    stage_complete: bool = False
    _room_manager: RoomManager = field(default_factory=RoomManager)
    _on_transition: TransitionCallback | None = None
    _on_stage_complete: StageCompleteCallback | None = None

    # -- Properties --

    @property
    def current_floor(self) -> FloorData:
        """The FloorData of the floor currently being played."""
        return self.stage_data.floors[self.floor_index]

    @property
    def current_room(self) -> Room | None:
        return self._room_manager.current_room

    @property
    def current_room_id(self) -> str | None:
        return self._room_manager.current_room_id

    # -- Callbacks --

    def on_transition(self, callback: TransitionCallback) -> None:
        """Register a callback fired after each room/floor transition."""
        self._on_transition = callback

    def on_stage_complete(self, callback: StageCompleteCallback) -> None:
        """Register a callback fired once when the stage exit is reached."""
        self._on_stage_complete = callback

    # -- Lifecycle --

    def start(self) -> Room:
        """Load the first floor and return its start room."""
        self.floor_index = 0
        self.stage_complete = False
        return self._room_manager.load_floor(self.current_floor)

    def resume_at(self, floor_index: int) -> Room:
        """Load a specific floor (mid-run checkpoint restore, Phase 14/15).

        The room-level position inside the floor is restored by the scene
        (it owns the player/camera); this only re-positions the floor.
        """
        if floor_index < 0 or floor_index >= len(self.stage_data.floors):
            raise IndexError(
                f"floor index {floor_index} out of range "
                f"(0..{len(self.stage_data.floors) - 1})"
            )
        self.floor_index = floor_index
        self.stage_complete = False
        return self._room_manager.load_floor(self.current_floor)

    # -- Transitions --

    def check_transition(self, player_box: AABB) -> Door | None:
        """Return the door the player overlaps in the current room, if any."""
        return self._room_manager.check_transition(player_box)

    def transition(self, door: Door) -> Room:
        """Execute a transition: room→room, floor→floor, or stage complete.

        Returns the current Room after the transition (unchanged when the
        stage just completed or was already complete).
        """
        if door.target_room == FLOOR_EXIT_TARGET:
            return self._advance_floor()
        room = self._room_manager.load_room(door.target_room)
        if self._on_transition is not None:
            spawn_x, spawn_y = door.target_spawn
            self._on_transition(room, spawn_x, spawn_y)
        return room

    def _advance_floor(self) -> Room:
        current = self._room_manager.current_room
        if current is None:
            raise RuntimeError("Cannot advance floor: no room loaded")
        if self.stage_complete:
            return current
        if self.floor_index + 1 >= len(self.stage_data.floors):
            self.stage_complete = True
            if self._on_stage_complete is not None:
                self._on_stage_complete()
            return current
        self.floor_index += 1
        room = self._room_manager.load_floor(self.current_floor)
        if self._on_transition is not None:
            spawn_x, spawn_y = room.player_spawn
            self._on_transition(room, spawn_x, spawn_y)
        return room
