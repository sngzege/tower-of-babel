"""Scene registration and switching.

Phase 2 scope: a single active scene with enter/exit transitions. A scene
stack (for pause overlays etc.) can be added later without changing the Scene
interface.
"""

from __future__ import annotations

from core.enums import SceneID
from engine.scene import Scene
from input.input_manager import ActionFrame
from rendering.renderer import Renderer


class SceneManager:
    """Owns the registered scenes and the one currently active."""

    def __init__(self) -> None:
        self._scenes: dict[SceneID, Scene] = {}
        self._active: Scene | None = None

    @property
    def active(self) -> Scene | None:
        return self._active

    def register(self, scene: Scene) -> None:
        if scene.scene_id in self._scenes:
            raise ValueError(f"Scene already registered: {scene.scene_id}")
        self._scenes[scene.scene_id] = scene

    def switch_to(self, scene_id: SceneID) -> None:
        if scene_id not in self._scenes:
            raise KeyError(f"Unknown scene: {scene_id}")
        if self._active is not None:
            self._active.exit()
        self._active = self._scenes[scene_id]
        self._active.enter()

    def update(self, frame: ActionFrame, dt: float) -> None:
        if self._active is not None:
            self._active.update(frame, dt)

    def render(self, renderer: Renderer) -> None:
        if self._active is not None:
            self._active.render(renderer)
