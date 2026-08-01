"""NPC framework: service NPCs with milestone arrival and service tiers.

An NPC is defined in data (data/npcs/*.yaml, schema npc.schema.yaml) and its
*state* (arrived, service_tier) lives in persistent village progression.
Each NPC hosts one service (loadout / run_prep / upgrades — placeholder
vocabulary, developer-owned) and follows one progression track (service
tier) whose levels gate service options.

Milestone-driven arrival: an NPC arrives when its arrival trigger milestone
is recorded (e.g. first boss kill). The milestone set is owned by the
meta-progression system (Phase 13); this module only reads it.

Dialogue is data: a dict of line ids -> text. Localization is deferred
(VERTICAL_SLICE.md §3); greybox lines are neutral placeholders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

MilestoneSet = frozenset[str]


class NPCError(ValueError):
    """Raised when an NPC document or state transition is invalid."""


@dataclass(frozen=True)
class ServiceTierLevel:
    """One service-tier level: milestone requirement + unlocked option ids."""

    index: int
    requires_milestone: str = ""
    unlocks: tuple[str, ...] = ()

    @classmethod
    def from_document(cls, document: dict[str, Any], index: int) -> ServiceTierLevel:
        raw_unlocks = document.get("unlocks", [])
        if not isinstance(raw_unlocks, list):
            raise NPCError(f"service tier {index} 'unlocks' must be a list")
        return cls(
            index=index,
            requires_milestone=str(document.get("requires_milestone", "")),
            unlocks=tuple(str(uid) for uid in raw_unlocks),
        )


@dataclass(frozen=True)
class NPC:
    """Static NPC definition (from data) + persistent state."""

    npc_id: str
    name: str
    service: str
    building_id: str
    arrival_trigger: str
    service_tier_levels: tuple[ServiceTierLevel, ...] = ()
    dialogue: dict[str, str] = field(default_factory=dict)
    tags: frozenset[str] = frozenset()
    arrived: bool = False
    service_tier: int = 0

    @classmethod
    def from_document(
        cls, document: dict[str, Any], *, arrived: bool = False, service_tier: int = 0
    ) -> NPC:
        npc_id = str(document.get("id", ""))
        if not npc_id:
            raise NPCError("NPC document missing 'id'")
        arrival = document.get("arrival")
        if not isinstance(arrival, dict):
            raise NPCError(f"NPC '{npc_id}' missing 'arrival' mapping")
        trigger = str(arrival.get("trigger", ""))
        if not trigger:
            raise NPCError(f"NPC '{npc_id}' arrival.trigger must be a milestone id")

        tracks = document.get("tracks") or {}
        service_tier_doc = tracks.get("service_tier") if isinstance(tracks, dict) else None
        levels: tuple[ServiceTierLevel, ...] = ()
        if isinstance(service_tier_doc, dict):
            raw_levels = service_tier_doc.get("levels", [])
            if isinstance(raw_levels, list):
                levels = tuple(
                    ServiceTierLevel.from_document(level_doc, index)
                    for index, level_doc in enumerate(raw_levels)
                )

        raw_dialogue = document.get("dialogue") or {}
        dialogue = (
            {str(k): str(v) for k, v in raw_dialogue.items()}
            if isinstance(raw_dialogue, dict)
            else {}
        )
        return cls(
            npc_id=npc_id,
            name=str(document.get("name", npc_id)),
            service=str(document.get("service", "")),
            building_id=str(document.get("building_id", "")),
            arrival_trigger=trigger,
            service_tier_levels=levels,
            dialogue=dialogue,
            tags=frozenset(str(tag) for tag in document.get("tags", [])),
            arrived=arrived,
            service_tier=service_tier if service_tier >= 0 else 0,
        )

    # -- Milestone arrival --

    def check_arrival(self, milestones: MilestoneSet) -> bool:
        """True when the NPC's arrival trigger milestone is recorded."""
        return self.arrival_trigger in milestones

    # -- Service tier --

    @property
    def max_service_tier(self) -> int:
        return len(self.service_tier_levels)

    @property
    def current_level(self) -> ServiceTierLevel | None:
        """The active service-tier level (or None when no levels are defined)."""
        if not self.service_tier_levels:
            return None
        idx = min(self.service_tier, len(self.service_tier_levels) - 1)
        return self.service_tier_levels[idx]

    def earned_service_unlocks(self) -> tuple[str, ...]:
        """All service options unlocked so far across reached tiers."""
        return tuple(
            unlock
            for level in self.service_tier_levels[: self.service_tier + 1]
            for unlock in level.unlocks
        )

    def service_options(self) -> tuple[str, ...]:
        """Service options currently offered by this NPC."""
        return self.earned_service_unlocks()

    def advance_service_tier(self, milestones: MilestoneSet) -> bool:
        """Advance the service tier if the next level's milestone is met.

        Returns True when the tier advanced. This is the NPC side of the
        slice requirement: a service tier unlocks a new option after the
        boss is defeated.
        """
        next_index = self.service_tier + 1
        if next_index >= len(self.service_tier_levels):
            return False
        next_level = self.service_tier_levels[next_index]
        if next_level.requires_milestone and next_level.requires_milestone not in milestones:
            return False
        # Rebuild with the new tier (frozen dataclass).
        object.__setattr__(self, "service_tier", next_index)
        return True

    def dialogue_line(self, key: str, default: str = "") -> str:
        """Look up a dialogue line by id; falls back to ``default``."""
        return self.dialogue.get(key, default)

    # -- Serialization --

    def to_state(self) -> dict[str, Any]:
        return {"id": self.npc_id, "arrived": self.arrived, "service_tier": self.service_tier}

    @classmethod
    def state_from(cls, document: dict[str, Any], state: dict[str, Any]) -> NPC:
        return cls.from_document(
            document,
            arrived=bool(state.get("arrived", False)),
            service_tier=int(state.get("service_tier", 0)),
        )


class NPCService:
    """Owns the NPC roster (definitions merged with persistent state)."""

    def __init__(self, npcs: list[NPC] | None = None) -> None:
        self._npcs: dict[str, NPC] = {npc.npc_id: npc for npc in (npcs or [])}

    @classmethod
    def from_registry_documents(
        cls, documents: list[dict[str, Any]], saved_state: dict[str, Any] | None = None
    ) -> NPCService:
        saved = saved_state or {}
        saved_npcs = saved.get("npcs") or {}
        npcs: list[NPC] = []
        for document in documents:
            npc_id = str(document.get("id", ""))
            state = saved_npcs.get(npc_id, {})
            npcs.append(
                NPC.state_from(document, state if isinstance(state, dict) else {})
            )
        return cls(npcs)

    def all(self) -> tuple[NPC, ...]:
        return tuple(self._npcs.values())

    def get(self, npc_id: str) -> NPC:
        try:
            return self._npcs[npc_id]
        except KeyError as exc:
            raise NPCError(f"unknown NPC '{npc_id}'") from exc

    def update(self, npc: NPC) -> None:
        self._npcs[npc.npc_id] = npc

    def reconcile_arrivals(self, milestones: MilestoneSet) -> int:
        """Mark all NPCs whose arrival trigger is met as arrived.

        Returns the number of NPCs that newly arrived.
        """
        count = 0
        for npc_id, npc in self._npcs.items():
            if not npc.arrived and npc.check_arrival(milestones):
                npc = NPC(
                    npc_id=npc.npc_id,
                    name=npc.name,
                    service=npc.service,
                    building_id=npc.building_id,
                    arrival_trigger=npc.arrival_trigger,
                    service_tier_levels=npc.service_tier_levels,
                    dialogue=npc.dialogue,
                    tags=npc.tags,
                    arrived=True,
                    service_tier=npc.service_tier,
                )
                self._npcs[npc_id] = npc
                count += 1
        return count

    def reconcile_service_tiers(self, milestones: MilestoneSet) -> int:
        """Advance service tiers where the next level's milestone is met."""
        count = 0
        for npc_id, npc in self._npcs.items():
            before = npc.service_tier
            if npc.advance_service_tier(milestones):
                self._npcs[npc_id] = npc
                if npc.service_tier > before:
                    count += 1
        return count

    def arrived_npcs(self) -> tuple[NPC, ...]:
        return tuple(npc for npc in self._npcs.values() if npc.arrived)

    def to_state(self) -> dict[str, Any]:
        return {
            "npcs": {npc_id: npc.to_state() for npc_id, npc in self._npcs.items()}
        }
