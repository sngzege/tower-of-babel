"""Abstract action input (Phase 2).

Gameplay consumes ActionFrame snapshots - it never sees keys, buttons, or
pygame. Device adapters (keyboard.py, controller.py) are the only pygame-aware
input modules. Action bindings come from config/input.yaml.

The action set encodes the locked control philosophy (DESIGN_DECISIONS.md L5)
while remaining data-bound, so future actions can be added without redesign.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class Action(Enum):
    """Abstract gameplay actions (locked layout: DESIGN_DECISIONS.md L5)."""

    PRIMARY_ATTACK = "primary_attack"  # Left Mouse
    CLASS_SKILL = "class_skill"  # Right Mouse
    SKILL_1 = "skill_1"  # Q
    SKILL_2 = "skill_2"  # E
    ULTIMATE = "ultimate"  # R
    AURA = "aura"  # T (aura / reserved-mana skill)
    DODGE = "dodge"  # Space
    INTERACT = "interact"
    PAUSE = "pause"


@dataclass(frozen=True)
class DeviceSnapshot:
    """Raw device state for one frame (adapter output)."""

    pressed: frozenset[str] = frozenset()  # raw control names that went down
    held: frozenset[str] = frozenset()  # raw control names currently down
    released: frozenset[str] = frozenset()  # raw control names that went up
    axis_x: float = 0.0  # movement axis -1..1
    axis_y: float = 0.0
    quit_requested: bool = False


class InputDevice(Protocol):
    """A pygame-aware adapter producing one snapshot per frame."""

    def snapshot(self) -> DeviceSnapshot: ...


@dataclass(frozen=True)
class ActionFrame:
    """Abstract input for one frame (gameplay-facing)."""

    pressed: frozenset[Action] = frozenset()
    held: frozenset[Action] = frozenset()
    released: frozenset[Action] = frozenset()
    move_x: float = 0.0
    move_y: float = 0.0
    quit_requested: bool = False


class InputManager:
    """Resolves device snapshots into ActionFrames using configured bindings."""

    def __init__(
        self,
        devices: list[InputDevice],
        bindings: dict[str, dict[str, str]],
    ) -> None:
        self._devices = list(devices)
        self._raw_to_action: dict[str, Action] = {}
        for device_map in bindings.values():
            for action_name, raw_name in device_map.items():
                try:
                    self._raw_to_action[raw_name] = Action(action_name)
                except ValueError:
                    raise ValueError(
                        f"Unknown action in bindings: {action_name}"
                    ) from None

    def poll(self) -> ActionFrame:
        """Collect every device snapshot and resolve it into an ActionFrame."""
        pressed: set[Action] = set()
        held: set[Action] = set()
        released: set[Action] = set()
        move_x = 0.0
        move_y = 0.0
        quit_requested = False
        for device in self._devices:
            snap = device.snapshot()
            for raw in snap.pressed:
                action = self._raw_to_action.get(raw)
                if action is not None:
                    pressed.add(action)
            for raw in snap.held:
                action = self._raw_to_action.get(raw)
                if action is not None:
                    held.add(action)
            for raw in snap.released:
                action = self._raw_to_action.get(raw)
                if action is not None:
                    released.add(action)
            move_x += snap.axis_x
            move_y += snap.axis_y
            quit_requested = quit_requested or snap.quit_requested
        return ActionFrame(
            pressed=frozenset(pressed),
            held=frozenset(held),
            released=frozenset(released),
            move_x=_clamp(move_x),
            move_y=_clamp(move_y),
            quit_requested=quit_requested,
        )


def _clamp(value: float) -> float:
    return max(-1.0, min(1.0, value))
