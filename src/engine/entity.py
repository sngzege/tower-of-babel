"""Game entities (hybrid model, approved 2026-07-27).

An Entity is a lightweight identity plus a bag of components. It knows nothing
about gameplay, rendering, or physics - concrete behavior arrives via
components and systems. Infrastructure only.
"""

from __future__ import annotations

import itertools
from typing import TypeVar, cast

from engine.component import Component

C = TypeVar("C", bound=Component)

_uids = itertools.count(1)


class Entity:
    """A named game object composed of components."""

    def __init__(self, name: str = "", uid: int | None = None) -> None:
        self.uid: int = uid if uid is not None else next(_uids)
        self.name: str = name
        self._components: dict[type[Component], Component] = {}

    def add(self, component: C) -> C:
        """Attach a component (one per component type). Returns it."""
        kind = type(component)
        if kind in self._components:
            raise ValueError(f"{self} already has component {kind.__name__}")
        self._components[kind] = component
        return component

    def get(self, kind: type[C]) -> C:
        try:
            return cast(C, self._components[kind])
        except KeyError as exc:
            raise KeyError(f"{self} has no component {kind.__name__}") from exc

    def has(self, kind: type[Component]) -> bool:
        return kind in self._components

    def remove(self, kind: type[Component]) -> None:
        self._components.pop(kind, None)

    def components(self) -> tuple[Component, ...]:
        return tuple(self._components.values())

    def __repr__(self) -> str:
        label = self.name or "entity"
        return f"<Entity #{self.uid} {label}>"
