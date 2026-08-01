"""Persistent state container: the saveable meta-game state (Phase 14).

Bundles the three persistent state owners into one payload so the save
system has a single ``persistent`` slot to write:

  - village (VillageState: town level, resources, building tiers)
  - npcs (NPCService: arrivals, service tiers)
  - progression (MetaProgression: mastery, milestones, records)

The container is the composition root for the meta-game: scenes receive it
and read/write through it. It builds itself from data documents (definitions)
plus an optional saved payload (state) — the standard pattern used by every
state owner in this codebase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gameplay.progression.meta_progression import MetaProgression
from gameplay.village.npc import NPCService
from gameplay.village.village import VillageState


@dataclass
class PersistentState:
    """Persistent meta-game state (serialized under save['persistent'])."""

    village: VillageState = field(default_factory=VillageState)
    npcs: NPCService = field(default_factory=NPCService)
    progression: MetaProgression = field(default_factory=MetaProgression)

    # -- Construction --

    @classmethod
    def from_save(
        cls,
        *,
        village_documents: list[dict[str, Any]],
        npc_documents: list[dict[str, Any]],
        mastery_documents: list[dict[str, Any]],
        unlock_documents: list[dict[str, Any]],
        saved_persistent: dict[str, Any] | None = None,
    ) -> PersistentState:
        saved = saved_persistent or {}
        return cls(
            village=VillageState.from_registry_documents(
                village_documents, saved.get("village")
            ),
            npcs=NPCService.from_registry_documents(
                npc_documents, saved.get("npcs")
            ),
            progression=MetaProgression.from_documents(
                mastery_documents,
                unlock_documents,
                saved.get("progression"),
            ),
        )

    # -- Run-result intake --

    def apply_run_result(self, result: Any) -> None:
        """Feed a finished run into village rewards + progression records."""
        self.village.apply_run_result(result)
        self.progression.record_run_result(result)
        # Milestone-driven unlocks: reconcile NPC arrivals + service tiers
        # now that new milestones (e.g. first boss kill) may be recorded.
        self.npcs.reconcile_arrivals(self.progression.milestone_set)
        self.npcs.reconcile_service_tiers(self.progression.milestone_set)

    # -- Serialization --

    def to_save(self) -> dict[str, Any]:
        return {
            "village": self.village.to_state(),
            "npcs": self.npcs.to_state(),
            "progression": self.progression.to_state(),
        }
