"""Gamepad adapter (pygame-aware input module).

Wraps pygame's joystick API and exposes buttons/axes as raw control names
("button_a", "right_trigger", ...). The left stick feeds the movement axes,
the right stick feeds the directional aim channel (twin-stick architecture,
pre-Phase-4 requirement). Both have configurable deadzones. Safe with zero
controllers connected.

NOTE: uses the stable pygame.joystick API. The _sdl2.controller module is
still flagged experimental upstream (FRAMEWORK_EVALUATION.md section 7) and
can replace this implementation later without changing InputManager.
"""

from __future__ import annotations

from input.input_manager import DeviceSnapshot

_BUTTON_NAMES = {
    0: "button_a",
    1: "button_b",
    2: "button_x",
    3: "button_y",
    4: "left_shoulder",
    5: "right_shoulder",
    6: "back",
    7: "start",
    9: "left_stick",
    10: "right_stick",
}

_TRIGGER_AXES = ((2, "left_trigger"), (5, "right_trigger"))

# Typical Xbox / dual-stick gamepad mapping: axes 0,1 = left stick;
# axes 3,4 = right stick (SDL mapping for Xbox One S on Windows).
_RIGHT_STICK_X = 3
_RIGHT_STICK_Y = 4


class Gamepad:
    """Polls the first connected gamepad via pygame.joystick."""

    def __init__(self, deadzone: float = 0.2) -> None:
        import pygame

        self._pygame = pygame
        self._deadzone = deadzone
        self._joystick = None
        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            self._joystick = pygame.joystick.Joystick(0)
            self._joystick.init()

    @property
    def connected(self) -> bool:
        return self._joystick is not None

    def snapshot(self) -> DeviceSnapshot:
        if self._joystick is None:
            return DeviceSnapshot()
        pygame = self._pygame
        pressed: set[str] = set()
        released: set[str] = set()
        for event in pygame.event.get([pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP]):
            name = _BUTTON_NAMES.get(event.button)
            if name is None:
                continue
            if event.type == pygame.JOYBUTTONDOWN:
                pressed.add(name)
            else:
                released.add(name)
        held = {
            name
            for button, name in _BUTTON_NAMES.items()
            if button < self._joystick.get_numbuttons()
            and self._joystick.get_button(button)
        }
        axis_x = self._apply_deadzone(self._joystick.get_axis(0))
        axis_y = self._apply_deadzone(self._joystick.get_axis(1))

        num_axes = self._joystick.get_numaxes()
        aim_axis_x = 0.0
        aim_axis_y = 0.0
        if num_axes > _RIGHT_STICK_X:
            aim_axis_x = self._apply_deadzone(self._joystick.get_axis(_RIGHT_STICK_X))
        if num_axes > _RIGHT_STICK_Y:
            aim_axis_y = self._apply_deadzone(self._joystick.get_axis(_RIGHT_STICK_Y))

        # Triggers count as digital actions when pulled past halfway (PROVISIONAL).
        for axis_index, name in _TRIGGER_AXES:
            if axis_index < num_axes and self._joystick.get_axis(axis_index) > 0.5:
                held.add(name)
        return DeviceSnapshot(
            pressed=frozenset(pressed),
            held=frozenset(held),
            released=frozenset(released),
            axis_x=axis_x,
            axis_y=axis_y,
            aim_axis_x=aim_axis_x,
            aim_axis_y=aim_axis_y,
        )

    def _apply_deadzone(self, value: float) -> float:
        if abs(value) < self._deadzone:
            return 0.0
        return value
