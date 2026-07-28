"""Passive system: permanent modifiers that don't require activation.

Passives modify the player's stats or behavior automatically when added to
the build. They are data-driven from data/passives/*.yaml.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gameplay.builds.build_state import BuildComponent, StatModifier


@dataclass(frozen=True)
class PassiveData(BuildComponent):
    """Data-driven passive ability.

    ``modifiers`` — list of StatModifiers to apply when this passive is active.
    ``stackable`` — can this passive be picked multiple times?
    ``max_stacks`` — maximum number of stacks.
    """
    modifiers: tuple[StatModifier, ...] = field(default_factory=tuple)
    stackable: bool = False
    max_stacks: int = 1

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> PassiveData:
        raw_mods = document.get("modifiers", [])
        modifiers = []
        for mod in raw_mods:
            modifiers.append(StatModifier(
                stat=str(mod.get("stat", "")),
                value=float(mod.get("value", 0.0)),
                is_percent=bool(mod.get("is_percent", False)),
                source=str(document.get("id", "unknown")),
                tags=frozenset(mod.get("tags", [])),
                condition=str(mod.get("condition", "")),
            ))
        return cls(
            id=str(document.get("id", "unknown")),
            name=str(document.get("name", "Unknown")),
            description=str(document.get("description", "")),
            tags=frozenset(document.get("tags", [])),
            modifiers=tuple(modifiers),
            stackable=bool(document.get("stackable", False)),
            max_stacks=int(document.get("max_stacks", 1)),
        )


# PROVISIONAL modifier definition helpers (extend for future phases).
_MODIFIER_REGISTRY: dict[str, type] = {}


def register_modifier_type(name: str, cls: type) -> None:
    _MODIFIER_REGISTRY[name] = cls
