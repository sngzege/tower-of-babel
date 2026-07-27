"""Tests for input.input_manager action mapping (Phase 2, framework-free)."""

from __future__ import annotations

import pytest

from input.input_manager import Action, DeviceSnapshot, InputManager

BINDINGS = {
    "keyboard": {"dodge": "space", "skill_1": "q", "pause": "escape"},
    "gamepad": {"dodge": "button_a"},
}


class _FakeDevice:
    def __init__(self, snapshot: DeviceSnapshot) -> None:
        self._snapshot = snapshot

    def snapshot(self) -> DeviceSnapshot:
        return self._snapshot


def _manager(snapshot: DeviceSnapshot) -> InputManager:
    return InputManager(devices=[_FakeDevice(snapshot)], bindings=BINDINGS)


def test_action_mapping_keyboard() -> None:
    frame = _manager(
        DeviceSnapshot(pressed=frozenset({"space"}), held=frozenset({"space"}))
    ).poll()
    assert Action.DODGE in frame.pressed
    assert Action.DODGE in frame.held
    assert Action.DODGE not in frame.released


def test_released_mapping() -> None:
    frame = _manager(DeviceSnapshot(released=frozenset({"q"}))).poll()
    assert Action.SKILL_1 in frame.released


def test_multiple_devices_merge() -> None:
    keyboard = _FakeDevice(DeviceSnapshot(held=frozenset({"space"})))
    gamepad = _FakeDevice(
        DeviceSnapshot(pressed=frozenset({"button_a"}), held=frozenset({"button_a"}))
    )
    frame = InputManager(devices=[keyboard, gamepad], bindings=BINDINGS).poll()
    assert Action.DODGE in frame.pressed  # gamepad contributed the press
    assert Action.DODGE in frame.held  # both contribute held


def test_unbound_raw_inputs_are_ignored() -> None:
    frame = _manager(DeviceSnapshot(held=frozenset({"f7", "mouse_middle"}))).poll()
    assert frame.held == frozenset()


def test_axes_clamped() -> None:
    frame = _manager(DeviceSnapshot(axis_x=0.9, axis_y=-2.0)).poll()
    assert frame.move_x == pytest.approx(0.9)
    assert frame.move_y == pytest.approx(-1.0)


def test_quit_flag_propagates() -> None:
    frame = _manager(DeviceSnapshot(quit_requested=True)).poll()
    assert frame.quit_requested is True


def test_unknown_action_in_bindings_raises() -> None:
    with pytest.raises(ValueError):
        InputManager(devices=[], bindings={"keyboard": {"not_an_action": "x"}})
