"""Unlock engine: milestone-driven content gates feeding reward pools.

An unlock is defined in data (data/unlocks/*.yaml, schema unlock.schema.yaml):
a ``source`` milestone (e.g. first_boss_kill), prerequisites, and ``grants``
(content ids injected into reward pools once the unlock is earned).

The engine is data-driven and rule-agnostic: it computes *which* unlocks are
earned from a milestone set and which content ids they grant. Consumers
(boon pool, weapon choices, NPC services) decide how to use the grants.

Greybox scope (RULES.md §0): one placeholder unlock (first boss -> boon).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

MilestoneSet = frozenset[str]


class UnlockError(ValueError):
    """Raised when an unlock document is invalid."""


@dataclass(frozen=True)
class Unlock:
    """Static unlock definition."""

    unlock_id: str
    name: str
    kind: str
    source: str
    requires: tuple[str, ...] = ()
    grants: tuple[str, ...] = ()
    tags: frozenset[str] = frozenset()

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> Unlock:
        unlock_id = str(document.get("id", ""))
        if not unlock_id:
            raise UnlockError("unlock document missing 'id'")
        raw_requires = document.get("requires", [])
        raw_grants = document.get("grants", [])
        if not isinstance(raw_requires, list) or not isinstance(raw_grants, list):
            raise UnlockError(f"unlock '{unlock_id}' requires/grants must be lists")
        return cls(
            unlock_id=unlock_id,
            name=str(document.get("name", unlock_id)),
            kind=str(document.get("kind", "")),
            source=str(document.get("source", "")),
            requires=tuple(str(rid) for rid in raw_requires),
            grants=tuple(str(gid) for gid in raw_grants),
            tags=frozenset(str(tag) for tag in document.get("tags", [])),
        )

    def is_earned(self, milestones: MilestoneSet, unlocked_others: frozenset[str]) -> bool:
        """True when the source milestone and prerequisites are satisfied."""
        if self.source and self.source not in milestones:
            return False
        return all(prereq in unlocked_others for prereq in self.requires)


@dataclass
class UnlockEngine:
    """Owns unlock definitions and computes earned grants."""

    unlocks: dict[str, Unlock] = field(default_factory=dict)

    @classmethod
    def from_registry_documents(cls, documents: list[dict[str, Any]]) -> UnlockEngine:
        return cls(
            unlocks={
                str(doc.get("id", "")): Unlock.from_document(doc)
                for doc in documents
            }
        )

    def all(self) -> tuple[Unlock, ...]:
        return tuple(self.unlocks.values())

    def earned(self, milestones: MilestoneSet) -> tuple[Unlock, ...]:
        """Unlocks whose milestone source + prerequisites are satisfied."""
        unlocked_ids: set[str] = set()
        # Iterate to fixpoint: a newly earned unlock may satisfy another's
        # prerequisite. Data is small; simplicity wins (RULES.md §15).
        changed = True
        while changed:
            changed = False
            for unlock in self.unlocks.values():
                if unlock.unlock_id in unlocked_ids:
                    continue
                if unlock.is_earned(milestones, frozenset(unlocked_ids)):
                    unlocked_ids.add(unlock.unlock_id)
                    changed = True
        return tuple(
            unlock for unlock in self.unlocks.values() if unlock.unlock_id in unlocked_ids
        )

    def earned_ids(self, milestones: MilestoneSet) -> frozenset[str]:
        return frozenset(unlock.unlock_id for unlock in self.earned(milestones))

    def granted_ids(self, milestones: MilestoneSet) -> frozenset[str]:
        """All content ids granted by earned unlocks."""
        return frozenset(
            grant
            for unlock in self.earned(milestones)
            for grant in unlock.grants
        )

    def granted_by_kind(self, milestones: MilestoneSet, kind: str) -> tuple[str, ...]:
        """Grants from earned unlocks of a given kind (e.g. 'boon_pool')."""
        return tuple(
            grant
            for unlock in self.earned(milestones)
            if unlock.kind == kind
            for grant in unlock.grants
        )
