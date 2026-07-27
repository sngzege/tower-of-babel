"""Generic finite state machine.

Will be used by scenes, player states, enemy AI, and boss phases - the machine
itself knows nothing about any of them. Infrastructure only.
"""

from __future__ import annotations

from collections.abc import Callable


class State:
    """A named state with optional enter/exit/update hooks."""

    def __init__(
        self,
        name: str,
        on_enter: Callable[[], None] | None = None,
        on_exit: Callable[[], None] | None = None,
        on_update: Callable[[float], None] | None = None,
    ) -> None:
        self.name = name
        self._on_enter = on_enter
        self._on_exit = on_exit
        self._on_update = on_update

    def enter(self) -> None:
        if self._on_enter:
            self._on_enter()

    def exit(self) -> None:
        if self._on_exit:
            self._on_exit()

    def update(self, dt: float) -> None:
        if self._on_update:
            self._on_update(dt)


class StateMachine:
    """Tracks one active state; can optionally restrict legal transitions."""

    def __init__(self, allowed_transitions: dict[str, set[str]] | None = None) -> None:
        self._states: dict[str, State] = {}
        self._current: State | None = None
        self._allowed = allowed_transitions

    @property
    def current(self) -> str | None:
        return self._current.name if self._current else None

    def add_state(self, state: State) -> None:
        if state.name in self._states:
            raise ValueError(f"Duplicate state: {state.name}")
        self._states[state.name] = state

    def set_state(self, name: str) -> None:
        if name not in self._states:
            raise KeyError(f"Unknown state: {name}")
        if self._current is not None:
            allowed = (self._allowed or {}).get(self._current.name)
            if allowed is not None and name not in allowed:
                raise ValueError(
                    f"Transition '{self._current.name}' -> '{name}' not allowed"
                )
            self._current.exit()
        self._current = self._states[name]
        self._current.enter()

    def update(self, dt: float) -> None:
        if self._current is not None:
            self._current.update(dt)
