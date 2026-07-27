"""Tests for engine.game_loop frame ordering (Phase 2, framework-free)."""

from __future__ import annotations

from core.enums import SceneID
from core.events import EventBus
from engine.game_loop import GameLoop
from engine.scene import Scene
from engine.scene_manager import SceneManager
from input.input_manager import DeviceSnapshot, InputManager

_FPS = 60


class _FakeDevice:
    def __init__(
        self, calls: list[str], snapshot: DeviceSnapshot | None = None
    ) -> None:
        self.calls = calls
        self._snapshot = snapshot or DeviceSnapshot()

    def snapshot(self) -> DeviceSnapshot:
        self.calls.append("poll")
        return self._snapshot


class _FakeScene(Scene):
    scene_id = SceneID.BOOT

    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def update(self, frame: object, dt: float) -> None:
        self.calls.append(f"update:{dt:.4f}")

    def render(self, renderer: object) -> None:
        self.calls.append("render")


class _FakeRenderer:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    @property
    def size(self) -> tuple[int, int]:
        return (100, 100)

    def clear(self, color: tuple[int, int, int]) -> None:
        self.calls.append("clear")

    def draw_rect(
        self, rect: tuple[int, int, int, int], color: tuple[int, int, int]
    ) -> None:
        self.calls.append("draw_rect")

    def present(self) -> None:
        self.calls.append("present")

    def tick(self, fps: int) -> float:
        self.calls.append("tick")
        return 1.0 / fps

    def close(self) -> None:
        pass


def _build(calls: list[str], snapshot: DeviceSnapshot | None = None) -> GameLoop:
    events = EventBus()
    events.subscribe("ping", lambda _event: calls.append("pong"))
    events.publish_deferred("ping")
    scenes = SceneManager()
    scenes.register(_FakeScene(calls))
    scenes.switch_to(SceneID.BOOT)
    calls.clear()
    renderer = _FakeRenderer(calls)
    return GameLoop(
        input_manager=InputManager(devices=[_FakeDevice(calls, snapshot)], bindings={}),
        scene_manager=scenes,
        event_bus=events,
        renderer=renderer,
        tick=renderer.tick,
        fps=_FPS,
    )


def test_frame_order_is_input_update_events_render() -> None:
    calls: list[str] = []
    loop = _build(calls)
    frames = loop.run(max_frames=1)
    assert frames == 1
    assert calls == [
        "tick",
        "poll",
        f"update:{1.0 / _FPS:.4f}",
        "pong",
        "clear",
        "render",
        "present",
    ]


def test_max_frames_stops_loop() -> None:
    calls: list[str] = []
    loop = _build(calls)
    assert loop.run(max_frames=3) == 3
    assert calls.count("tick") == 3


def test_quit_request_stops_loop() -> None:
    calls: list[str] = []
    loop = _build(calls, snapshot=DeviceSnapshot(quit_requested=True))
    assert loop.run(max_frames=99) == 1


def test_dt_comes_from_tick() -> None:
    calls: list[str] = []
    loop = _build(calls)
    loop.run(max_frames=1)
    assert f"update:{1.0 / _FPS:.4f}" in calls
