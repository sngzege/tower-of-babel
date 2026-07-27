"""Scene interface (engine layer).

A Scene is one application state (boot, menu, village, dungeon, ...). Scenes
consume abstract input (input.input_manager.ActionFrame) and draw through the
rendering.Renderer protocol - never pygame directly (adapter isolation,
2026-07-27).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.enums import SceneID
    from input.input_manager import ActionFrame
    from rendering.renderer import Renderer


class Scene(ABC):
    """Base class for application scenes."""

    scene_id: SceneID

    def enter(self) -> None:
        """Called when this scene becomes active."""

    def exit(self) -> None:
        """Called when this scene is replaced."""

    @abstractmethod
    def update(self, frame: ActionFrame, dt: float) -> None:
        """Advance scene state by ``dt`` seconds using abstract input."""

    @abstractmethod
    def render(self, renderer: Renderer) -> None:
        """Draw the scene through the renderer protocol."""
