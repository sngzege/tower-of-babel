"""Systems: behavior applied to entities by component requirement (hybrid model).

A System is intentionally simple: it filters entities by component types and
applies behavior. There is no scheduler, no event magic, no ECS framework
(docs/development/FRAMEWORK_EVALUATION.md section 6). Infrastructure only.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from engine.component import Component
from engine.entity import Entity


class System(ABC):
    """Processes entities that carry all ``required`` component types."""

    required: tuple[type[Component], ...] = ()

    def process(self, entities: Iterable[Entity], dt: float) -> int:
        """Update every matching entity. Returns how many were processed."""
        processed = 0
        for entity in entities:
            if all(entity.has(kind) for kind in self.required):
                self.update(entity, dt)
                processed += 1
        return processed

    @abstractmethod
    def update(self, entity: Entity, dt: float) -> None:
        """Apply the system's behavior to one matching entity."""
