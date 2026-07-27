"""Application owner: wires configuration, devices, scenes, and the loop.

Engine layer: orchestrates adapters but contains no gameplay and imports no
pygame (adapter isolation, 2026-07-27). Framework-specifics live behind the
Renderer protocol and the input device adapters.
"""

from __future__ import annotations

from core.dependency_container import DependencyContainer
from core.events import EventBus
from engine.game_loop import GameLoop
from engine.scene import Scene
from engine.scene_manager import SceneManager
from input.controller import Gamepad
from input.input_manager import InputDevice, InputManager
from input.keyboard import KeyboardMouse
from rendering.renderer import PygameRenderer, Renderer
from utils.config_loader import ConfigLoader
from utils.logger import get_logger

_logger = get_logger(__name__)


class Game:
    """Owns application state and runs the game loop (Phase 2 scope)."""

    def __init__(
        self,
        config: ConfigLoader,
        title: str = "Roguelike",
        vsync: bool | None = None,
    ) -> None:
        display = config.load("display")
        window = display.get("window", {})
        input_config = config.load("input")
        bindings = input_config.get("bindings", {})
        gamepad_config = input_config.get("gamepad", {})
        use_vsync = bool(window.get("vsync", True)) if vsync is None else vsync

        self.container = DependencyContainer()
        self.events = EventBus()
        self.renderer: Renderer = PygameRenderer(
            width=int(window.get("width", 1280)),
            height=int(window.get("height", 720)),
            title=title,
            vsync=use_vsync,
        )
        devices: list[InputDevice] = [KeyboardMouse()]
        if gamepad_config.get("enabled", True):
            devices.append(Gamepad(deadzone=float(gamepad_config.get("deadzone", 0.2))))
        self.input = InputManager(devices=devices, bindings=bindings)
        self.scenes = SceneManager()

        self.container.register_instance("events", self.events)
        self.container.register_instance("input", self.input)
        self.container.register_instance("scenes", self.scenes)
        self.container.register_instance("renderer", self.renderer)

    def register_scene(self, scene: Scene, *, initial: bool = False) -> None:
        self.scenes.register(scene)
        if initial:
            self.scenes.switch_to(scene.scene_id)

    def run(self, fps: int = 60, max_frames: int | None = None) -> int:
        """Build the loop and run it. Returns frames executed."""
        loop = GameLoop(
            input_manager=self.input,
            scene_manager=self.scenes,
            event_bus=self.events,
            renderer=self.renderer,
            tick=self.renderer.tick,
            fps=fps,
        )
        frames = loop.run(max_frames=max_frames)
        _logger.info("Game loop finished after %d frame(s)", frames)
        self.renderer.close()
        return frames
