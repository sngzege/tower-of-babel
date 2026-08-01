"""Building model: a village building plot with tiered upgrades.

A building is defined in data (data/village/buildings/*.yaml, schema
building.schema.yaml) and its *state* (current tier) lives in the village
persistent state. Tiers are data-driven: each tier has a cost, a visual
state id, and a list of unlock ids granted when the tier is reached.

Greybox scope (RULES.md §0): neutral names, two visual tiers (plot -> tier1),
placeholder costs. Balance is a human review pass after the game is playable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class BuildingError(ValueError):
    """Raised when a building document or upgrade attempt is invalid."""


@dataclass(frozen=True)
class BuildingTier:
    """One upgrade tier of a building."""

    index: int
    cost: dict[str, int] = field(default_factory=dict)
    unlocks: tuple[str, ...] = ()
    visual: str = "plot"

    @classmethod
    def from_document(cls, document: dict[str, Any], index: int) -> BuildingTier:
        raw_cost = document.get("cost", {})
        if not isinstance(raw_cost, dict):
            raise BuildingError(f"tier {index} 'cost' must be a mapping")
        cost = {
            str(resource): int(amount)
            for resource, amount in raw_cost.items()
        }
        raw_unlocks = document.get("unlocks", [])
        if not isinstance(raw_unlocks, list):
            raise BuildingError(f"tier {index} 'unlocks' must be a list")
        return cls(
            index=index,
            cost=cost,
            unlocks=tuple(str(uid) for uid in raw_unlocks),
            visual=str(document.get("visual", "plot")),
        )


@dataclass(frozen=True)
class Building:
    """Static building definition (from data) + current tier index (state)."""

    building_id: str
    name: str
    service: str
    plot: str
    tiers: tuple[BuildingTier, ...]
    tags: frozenset[str] = frozenset()
    current_tier: int = 0
    plot_rect: tuple[float, float, float, float] | None = None

    @classmethod
    def from_document(
        cls, document: dict[str, Any], current_tier: int = 0
    ) -> Building:
        """Build from a data/village/buildings document."""
        building_id = str(document.get("id", ""))
        if not building_id:
            raise BuildingError("building document missing 'id'")
        raw_tiers = document.get("tiers", [])
        if not isinstance(raw_tiers, list) or not raw_tiers:
            raise BuildingError(f"building '{building_id}' needs at least one tier")
        tiers = tuple(
            BuildingTier.from_document(tier_doc, index)
            for index, tier_doc in enumerate(raw_tiers)
        )
        if current_tier < 0 or current_tier >= len(tiers):
            raise BuildingError(
                f"building '{building_id}' current_tier {current_tier} out of range"
            )
        raw_rect = document.get("plot_rect")
        plot_rect: tuple[float, float, float, float] | None = None
        if isinstance(raw_rect, dict):
            plot_rect = (
                float(raw_rect.get("x", 0.0)),
                float(raw_rect.get("y", 0.0)),
                float(raw_rect.get("w", 0.0)),
                float(raw_rect.get("h", 0.0)),
            )
        return cls(
            building_id=building_id,
            name=str(document.get("name", building_id)),
            service=str(document.get("service", "")),
            plot=str(document.get("plot", "")),
            tiers=tiers,
            tags=frozenset(str(tag) for tag in document.get("tags", [])),
            current_tier=current_tier,
            plot_rect=plot_rect,
        )

    # -- Queries --

    @property
    def tier(self) -> BuildingTier:
        """The currently active tier."""
        return self.tiers[self.current_tier]

    @property
    def max_tier_reached(self) -> bool:
        return self.current_tier >= len(self.tiers) - 1

    @property
    def next_tier(self) -> BuildingTier | None:
        """The tier this building can be upgraded to, or None if maxed."""
        if self.max_tier_reached:
            return None
        return self.tiers[self.current_tier + 1]

    @property
    def visual_state(self) -> str:
        """Current visual state id (for the village scene)."""
        return self.tier.visual

    @property
    def earned_unlocks(self) -> tuple[str, ...]:
        """All unlock ids earned so far across reached tiers."""
        return tuple(
            unlock
            for tier in self.tiers[: self.current_tier + 1]
            for unlock in tier.unlocks
        )

    # -- Upgrades --

    def can_upgrade(self, resources: dict[str, int]) -> bool:
        """True if a next tier exists and every cost is affordable."""
        next_tier = self.next_tier
        if next_tier is None:
            return False
        return all(
            resources.get(resource, 0) >= amount
            for resource, amount in next_tier.cost.items()
        )

    def upgrade(self, resources: dict[str, int]) -> tuple[Building, dict[str, int]]:
        """Return (upgraded building, remaining resources) or raise.

        The caller (village) owns the resource dict; this method returns the
        remainder after paying for the next tier so state stays immutable.
        """
        next_tier = self.next_tier
        if next_tier is None:
            raise BuildingError(
                f"building '{self.building_id}' is already at max tier"
            )
        for resource, amount in next_tier.cost.items():
            if resources.get(resource, 0) < amount:
                raise BuildingError(
                    f"building '{self.building_id}' upgrade requires "
                    f"{amount} {resource} (have {resources.get(resource, 0)})"
                )
        remaining = dict(resources)
        for resource, amount in next_tier.cost.items():
            remaining[resource] -= amount
        upgraded = Building(
            building_id=self.building_id,
            name=self.name,
            service=self.service,
            plot=self.plot,
            tiers=self.tiers,
            tags=self.tags,
            current_tier=self.current_tier + 1,
            plot_rect=self.plot_rect,
        )
        return upgraded, remaining

    # -- Serialization --

    def to_state(self) -> dict[str, Any]:
        """Persistent-state payload (only the mutable bit: current tier)."""
        return {"id": self.building_id, "current_tier": self.current_tier}

    @classmethod
    def state_from(cls, document: dict[str, Any], state: dict[str, Any]) -> Building:
        """Rebuild from data document + saved state (roundtrip)."""
        current_tier = int(state.get("current_tier", 0))
        return cls.from_document(document, current_tier=current_tier)
