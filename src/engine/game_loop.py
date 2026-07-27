"""Frame orchestration: input -> update -> events -> render (framework-free).

Implements the Phase 2 loop order from IMPLEMENTATION_PLAN.md:

    tick (dt) -> poll input -> update scenes -> pump deferred events -> render

The loop knows interfaces only (InputManager, SceneManager, EventBus,
Renderer protocol, a tick callable) - no pygame, no gameplay.
"""

from __future__ import annotations

from collections.abc import Callable

from core.events import EventBus
from engine.scene_manager import SceneManager
from input.input_manager import ActionFrame, InputManager
from rendering.renderer import Color, Renderer

_CLEAR_COLOR: Color = (0, 0, 0)


class GameLoop:
    """Runs the frame loop until stopped or ``max_frames`` is reached."""

    def __init__(
        self,
        input_manager: InputManager,
        scene_manager: SceneManager,
        event_bus: EventBus,
        renderer: Renderer,
        tick: Callable[[int], float],
        fps: int = 60,
    ) -> None:
        self._input = input_manager
        self._scenes = scene_manager
        self._events = event_bus
        self._renderer = renderer
        self._tick = tick
        self._fps = fps
        self.running = False
        self.last_frame: ActionFrame | None = None

    def run(self, max_frames: int | None = None) -> int:
        """Execute the loop. Returns the number of frames executed."""
        self.running = True
        frames = 0
        while self.running:
            dt = self._tick(self._fps)
            frame = self._input.poll()
            self.last_frame = frame
            if frame.quit_requested:
                self.stop()
            self._scenes.update(frame, dt)
            self._events.pump()
            self._renderer.clear(_CLEAR_COLOR)
            self._scenes.render(self._renderer)
            self._renderer.present()
            frames += 1
            if max_frames is not None and frames >= max_frames:
                break
        return frames

    def stop(self) -> None:
        self.running = False
