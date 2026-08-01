"""Class mastery: data-driven per-class XP curve with milestone bonuses (L13).

A mastery curve is defined in data (data/progression/*.yaml, schema
progression.schema.yaml): ``xp_per_level`` and a list of bonuses granted at
specific mastery levels (permanent, global — L13). The curve is
rule-agnostic: a future design decision can change milestone intervals
without redesigning this module.

Greybox scope (RULES.md §0): placeholder values, Warrior only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class MasteryError(ValueError):
    """Raised when a mastery document is invalid."""


@dataclass(frozen=True)
class MasteryBonus:
    """A permanent global passive bonus granted at a mastery level."""

    at_level: int
    stat: str
    value: float
    is_percent: bool = False

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> MasteryBonus:
        return cls(
            at_level=int(document.get("at_level", 1)),
            stat=str(document.get("stat", "")),
            value=float(document.get("value", 0.0)),
            is_percent=bool(document.get("is_percent", False)),
        )


@dataclass(frozen=True)
class ClassMastery:
    """Static mastery curve for one class."""

    mastery_id: str
    class_id: str
    xp_per_level: int
    bonuses: tuple[MasteryBonus, ...] = ()
    tags: frozenset[str] = frozenset()

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> ClassMastery:
        mastery_id = str(document.get("id", ""))
        if not mastery_id:
            raise MasteryError("mastery document missing 'id'")
        raw_bonuses = document.get("bonuses", [])
        if not isinstance(raw_bonuses, list):
            raise MasteryError(f"mastery '{mastery_id}' 'bonuses' must be a list")
        return cls(
            mastery_id=mastery_id,
            class_id=str(document.get("class_id", "")),
            xp_per_level=int(document.get("xp_per_level", 100)),
            bonuses=tuple(MasteryBonus.from_document(doc) for doc in raw_bonuses),
            tags=frozenset(str(tag) for tag in document.get("tags", [])),
        )

    def xp_for_level(self, level: int) -> int:
        """XP needed to reach a mastery level (flat curve, placeholder).

        ``level`` is reserved for a future scaling curve; the current
        placeholder grants a constant XP cost per level.
        """
        return self.xp_per_level

    def bonuses_at_or_below(self, level: int) -> tuple[MasteryBonus, ...]:
        """All bonuses earned by the given mastery level (L13 milestones)."""
        return tuple(bonus for bonus in self.bonuses if bonus.at_level <= level)


@dataclass
class MasteryState:
    """Mutable per-class mastery progress (persistent)."""

    level: int = 1
    xp: int = 0

    def add_xp(self, curve: ClassMastery, amount: int) -> int:
        """Grant XP; level up as many times as possible.

        Returns the number of levels gained.
        """
        if amount <= 0:
            return 0
        self.xp += int(amount)
        gained = 0
        while self.xp >= curve.xp_for_level(self.level):
            self.xp -= curve.xp_for_level(self.level)
            self.level += 1
            gained += 1
        return gained

    def to_state(self) -> dict[str, Any]:
        return {"level": self.level, "xp": self.xp}

    @classmethod
    def state_from(cls, state: dict[str, Any]) -> MasteryState:
        return cls(
            level=int(state.get("level", 1)),
            xp=int(state.get("xp", 0)),
        )
