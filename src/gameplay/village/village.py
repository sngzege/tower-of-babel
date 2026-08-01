"""Village: the persistent meta-game hub (L11/L12 structure).

Owns:
  - persistent resources (Gold, Babylon Relics — L9)
  - Town Level (L12: gates building progression)
  - buildings (data-driven definitions + per-building tier state)

The village receives run results as plain data (RunResult), never touches
dungeon internals, and serializes only what it owns (ARCHITECTURE.md §6).

Greybox scope (RULES.md §0): two currencies with placeholder names, three
placeholder buildings, provisional upgrade costs. Balance is human-owned.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gameplay.village.building import Building

GOLD = "gold"
RELIC = "relics"

# Default resource amounts for a fresh save (provisional, not balance).
DEFAULT_RESOURCES: dict[str, int] = {GOLD: 0, RELIC: 0}


class VillageError(ValueError):
    """Raised on invalid village operations."""


@dataclass
class VillageState:
    """Persistent village state. Owned by the save system (Phase 14)."""

    town_level: int = 1
    resources: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_RESOURCES))
    # building_id -> Building (definitions merged from data + tier state)
    buildings: dict[str, Building] = field(default_factory=dict)

    # -- Construction --

    @classmethod
    def from_registry_documents(
        cls, documents: list[dict[str, Any]], saved_state: dict[str, Any] | None = None
    ) -> VillageState:
        """Build a village from building data documents (+ optional saved state).

        ``saved_state`` (from a save file) may carry: town_level, resources,
        and per-building ``current_tier`` values. Definitions always come from
        data so new tiers/content appear without migration.
        """
        saved = saved_state or {}
        village = cls(
            town_level=int(saved.get("town_level", 1)),
            resources={
                str(k): int(v)
                for k, v in (saved.get("resources") or DEFAULT_RESOURCES).items()
            },
        )
        saved_tiers = saved.get("buildings") or {}
        for document in documents:
            building_id = str(document.get("id", ""))
            tier_state = saved_tiers.get(building_id, {})
            village.buildings[building_id] = Building.state_from(
                document, tier_state if isinstance(tier_state, dict) else {}
            )
        return village

    # -- Resources --

    def add_resources(self, amounts: dict[str, int]) -> None:
        """Add resource amounts (e.g. run rewards)."""
        for resource, amount in amounts.items():
            self.resources[resource] = self.resources.get(resource, 0) + int(amount)

    def can_afford(self, cost: dict[str, int]) -> bool:
        return all(
            self.resources.get(resource, 0) >= amount
            for resource, amount in cost.items()
        )

    # -- Buildings --

    def get_building(self, building_id: str) -> Building:
        try:
            return self.buildings[building_id]
        except KeyError as exc:
            raise VillageError(f"unknown building '{building_id}'") from exc

    def building_tier(self, building_id: str) -> int:
        return self.get_building(building_id).current_tier

    def upgrade_building(self, building_id: str) -> Building:
        """Pay the next tier's cost and upgrade the building.

        Raises VillageError when the building is maxed, the cost is not
        affordable, or the town level gates the upgrade (L12 mutual gating:
        each tier above the first requires town_level >= tier index).
        """
        building = self.get_building(building_id)
        next_tier = building.next_tier
        if next_tier is None:
            raise VillageError(f"building '{building_id}' is already maxed")
        if next_tier.index > self.town_level:
            raise VillageError(
                f"building '{building_id}' needs town level {next_tier.index} "
                f"(current {self.town_level})"
            )
        if not building.can_upgrade(self.resources):
            raise VillageError(
                f"building '{building_id}' upgrade not affordable"
            )
        upgraded, remaining = building.upgrade(self.resources)
        self.resources = remaining
        self.buildings[building_id] = upgraded
        return upgraded

    def earned_unlocks(self) -> tuple[str, ...]:
        """Every unlock id granted by all reached building tiers."""
        return tuple(
            unlock
            for building in self.buildings.values()
            for unlock in building.earned_unlocks
        )

    # -- Run results --

    def apply_run_result(self, result: Any) -> None:
        """Apply a finished run's rewards to the village.

        ``result`` is a duck-typed RunResult: victory, gold_earned, and
        relics_earned are read if present (keeps village decoupled from the
        run package). Boss victory grants a relic; gold always banks.
        """
        gold = int(getattr(result, "gold_earned", 0) or 0)
        if gold > 0:
            self.add_resources({GOLD: gold})
        relics = int(getattr(result, "relics_earned", 0) or 0)
        victory = bool(getattr(result, "victory", False))
        if victory and relics <= 0:
            relics = 1  # provisional: boss victory grants one relic
        if relics > 0:
            self.add_resources({RELIC: relics})

    # -- Serialization --

    def to_state(self) -> dict[str, Any]:
        """Persistent-state payload for the save system."""
        return {
            "town_level": self.town_level,
            "resources": dict(self.resources),
            "buildings": {
                bid: building.to_state()
                for bid, building in self.buildings.items()
            },
        }
