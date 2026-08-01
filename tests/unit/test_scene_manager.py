"""Tests for engine.scene_manager (Phase 2)."""

from __future__ import annotations

import pytest

from core.enums import SceneID
from engine.scene import Scene
from engine.scene_manager import SceneManager


class _Scene(Scene):
    def __init__(self, scene_id: SceneID, calls: list[str]) -> None:
        self.scene_id = scene_id
        self.calls = calls

    def enter(self) -> None:
        self.calls.append(f"enter:{self.scene_id.name}")

    def exit(self) -> None:
        self.calls.append(f"exit:{self.scene_id.name}")

    def update(self, frame: object, dt: float) -> None:
        self.calls.append("update")

    def render(self, renderer: object) -> None:
        self.calls.append("render")


def test_switch_fires_enter_and_exit() -> None:
    calls: list[str] = []
    manager = SceneManager()
    manager.register(_Scene(SceneID.BOOT, calls))
    manager.register(_Scene(SceneID.MAIN_MENU, calls))
    manager.switch_to(SceneID.BOOT)
    manager.switch_to(SceneID.MAIN_MENU)
    assert calls == ["enter:BOOT", "exit:BOOT", "enter:MAIN_MENU"]
    assert manager.active is not None
    assert manager.active.scene_id == SceneID.MAIN_MENU


def test_unknown_scene_raises() -> None:
    with pytest.raises(KeyError):
        SceneManager().switch_to(SceneID.VILLAGE)


def test_duplicate_registration_raises() -> None:
    manager = SceneManager()
    manager.register(_Scene(SceneID.BOOT, []))
    with pytest.raises(ValueError):
        manager.register(_Scene(SceneID.BOOT, []))


def test_delegation_to_active_scene() -> None:
    calls: list[str] = []
    manager = SceneManager()
    manager.register(_Scene(SceneID.BOOT, calls))
    manager.switch_to(SceneID.BOOT)
    manager.update(None, 0.016)  # type: ignore[arg-type]
    manager.render(None)  # type: ignore[arg-type]
    assert calls == ["enter:BOOT", "update", "render"]


def test_no_active_scene_is_safe() -> None:
    manager = SceneManager()
    manager.update(None, 0.016)  # type: ignore[arg-type]
    manager.render(None)  # type: ignore[arg-type]
    assert manager.active is None


def test_replace_swaps_registered_scene() -> None:
    calls: list[str] = []
    manager = SceneManager()
    manager.register(_Scene(SceneID.DUNGEON, calls))
    manager.switch_to(SceneID.DUNGEON)
    # Replace the active scene with a fresh instance (new run).
    manager.replace(_Scene(SceneID.DUNGEON, calls))
    assert manager.active is not None
    assert manager.active.scene_id == SceneID.DUNGEON
    assert calls == ["enter:DUNGEON", "enter:DUNGEON"]  # re-enter on replace


def test_replace_registers_new_scene() -> None:
    calls: list[str] = []
    manager = SceneManager()
    manager.replace(_Scene(SceneID.VILLAGE, calls))
    manager.switch_to(SceneID.VILLAGE)
    assert manager.active is not None
    assert manager.active.scene_id == SceneID.VILLAGE
