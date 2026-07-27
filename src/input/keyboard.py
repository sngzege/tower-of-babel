"""Keyboard + mouse adapter (pygame-aware input module).

Translates pygame events and key states into DeviceSnapshots with stable raw
control names ("q", "space", "escape", "mouse_left", ...). Movement axes come
from WASD only; arrow keys feed the directional aim channel (approved
pre-Phase-4 requirement). The mouse cursor position and movement flag are
included for mouse-aim calculations. Only this module (and controller.py)
touches pygame's input APIs (adapter isolation).
"""

from __future__ import annotations

from typing import Any

from input.input_manager import DeviceSnapshot

_MOUSE_NAMES = {1: "mouse_left", 2: "mouse_middle", 3: "mouse_right"}

# WASD exclusively controls movement (arrows now go to the aim channel).
_MOVEMENT_KEYS: dict[str, tuple[float, float]] = {
    "w": (0.0, -1.0),
    "s": (0.0, 1.0),
    "a": (-1.0, 0.0),
    "d": (1.0, 0.0),
}

# Arrow keys control keyboard aim (directional, 8-way via DeviceSnapshot.aim_axis).
_AIM_KEYS: dict[str, tuple[float, float]] = {
    "up": (0.0, -1.0),
    "down": (0.0, 1.0),
    "left": (-1.0, 0.0),
    "right": (1.0, 0.0),
}


class KeyboardMouse:
    """Polls keyboard/mouse each frame via pygame."""

    def __init__(self) -> None:
        import pygame

        self._pygame = pygame
        self._key_names = _build_key_names(pygame)
        self._last_pointer: tuple[int, int] | None = None

    def snapshot(self) -> DeviceSnapshot:
        pygame = self._pygame
        pressed: set[str] = set()
        released: set[str] = set()
        quit_requested = False
        event_types = [
            pygame.QUIT,
            pygame.KEYDOWN,
            pygame.KEYUP,
            pygame.MOUSEBUTTONDOWN,
            pygame.MOUSEBUTTONUP,
        ]
        for event in pygame.event.get(event_types):
            if event.type == pygame.QUIT:
                quit_requested = True
            elif event.type == pygame.KEYDOWN:
                name = self._key_names.get(event.key)
                if name:
                    pressed.add(name)
            elif event.type == pygame.KEYUP:
                name = self._key_names.get(event.key)
                if name:
                    released.add(name)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                name = _MOUSE_NAMES.get(event.button)
                if name:
                    pressed.add(name)
            elif event.type == pygame.MOUSEBUTTONUP:
                name = _MOUSE_NAMES.get(event.button)
                if name:
                    released.add(name)

        held: set[str] = set()
        keys = pygame.key.get_pressed()
        for code, name in self._key_names.items():
            if keys[code]:
                held.add(name)
        mouse = pygame.mouse.get_pressed(num_buttons=3)
        for index, name in _MOUSE_NAMES.items():
            if mouse[index - 1]:
                held.add(name)

        axis_x = 0.0
        axis_y = 0.0
        for key_name, (dx, dy) in _MOVEMENT_KEYS.items():
            if key_name in held:
                axis_x += dx
                axis_y += dy

        aim_axis_x = 0.0
        aim_axis_y = 0.0
        for key_name, (dx, dy) in _AIM_KEYS.items():
            if key_name in held:
                aim_axis_x += dx
                aim_axis_y += dy

        pos = pygame.mouse.get_pos()
        pointer = (float(pos[0]), float(pos[1]))
        pointer_moved = (
            self._last_pointer is not None and pos != self._last_pointer
        )
        self._last_pointer = pos

        return DeviceSnapshot(
            pressed=frozenset(pressed),
            held=frozenset(held),
            released=frozenset(released),
            axis_x=axis_x,
            axis_y=axis_y,
            aim_axis_x=aim_axis_x,
            aim_axis_y=aim_axis_y,
            pointer=pointer,
            pointer_moved=pointer_moved,
            quit_requested=quit_requested,
        )


def _build_key_names(pygame: Any) -> dict[int, str]:
    names: dict[int, str] = {}
    for letter in range(pygame.K_a, pygame.K_z + 1):
        names[letter] = chr(letter)
    for digit in range(pygame.K_0, pygame.K_9 + 1):
        names[digit] = chr(digit)
    names[pygame.K_SPACE] = "space"
    names[pygame.K_ESCAPE] = "escape"
    names[pygame.K_RETURN] = "enter"
    names[pygame.K_TAB] = "tab"
    names[pygame.K_LSHIFT] = "shift"
    names[pygame.K_LCTRL] = "ctrl"
    names[pygame.K_UP] = "up"
    names[pygame.K_DOWN] = "down"
    names[pygame.K_LEFT] = "left"
    names[pygame.K_RIGHT] = "right"
    return names

