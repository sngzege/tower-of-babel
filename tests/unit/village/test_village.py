"""Phase 11 tests: Village Framework.

Verifies:
  - Building loads from data documents with tier structure
  - Tier upgrade pays cost and unlocks the tier's unlocks
  - Visual state mapping (plot -> tier1) follows the current tier
  - Town-level gating (L12 mutual gating)
  - Run result application (gold banks, boss victory grants a relic)
  - Persistence roundtrip (to_state/from state)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gameplay.village.building import Building, BuildingError
from gameplay.village.village import GOLD, RELIC, VillageError, VillageState

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"

BUILDING_A = {
    "id": "building_a",
    "name": "Workshop A",
    "service": "loadout",
    "plot": "plot_north",
    "tiers": [
        {"cost": {}, "unlocks": [], "visual": "plot"},
        {"cost": {"relics": 1}, "unlocks": ["service_loadout_tier1"], "visual": "tier1"},
    ],
}


class _FakeRunResult:
    def __init__(
        self,
        *,
        victory: bool = False,
        gold_earned: int = 0,
        relics_earned: int = 0,
    ) -> None:
        self.victory = victory
        self.gold_earned = gold_earned
        self.relics_earned = relics_earned


def _village(**overrides: object) -> VillageState:
    """A village with one building, optionally pre-seeded with resources."""
    village = VillageState.from_registry_documents([BUILDING_A])
    if "resources" in overrides:
        village.resources = dict(overrides["resources"])  # type: ignore[assignment]
    return village


# -- Building model --

def test_building_loads_tiers() -> None:
    building = Building.from_document(BUILDING_A)
    assert building.building_id == "building_a"
    assert len(building.tiers) == 2
    assert building.current_tier == 0
    assert building.visual_state == "plot"
    assert not building.max_tier_reached
    assert building.next_tier is not None
    assert building.next_tier.index == 1


def test_building_rejects_empty_tiers() -> None:
    with pytest.raises(BuildingError):
        Building.from_document({"id": "bad", "tiers": []})


def test_building_rejects_out_of_range_tier() -> None:
    with pytest.raises(BuildingError):
        Building.from_document(BUILDING_A, current_tier=5)


# -- Upgrade cost -> unlock --

def test_upgrade_pays_cost_and_grants_unlock() -> None:
    village = _village(resources={RELIC: 1, GOLD: 0})
    upgraded = village.upgrade_building("building_a")
    assert upgraded.current_tier == 1
    assert village.building_tier("building_a") == 1
    assert village.resources[RELIC] == 0  # cost paid
    assert "service_loadout_tier1" in village.earned_unlocks()


def test_upgrade_rejected_without_resources() -> None:
    village = _village(resources={RELIC: 0})
    with pytest.raises(VillageError, match="not affordable"):
        village.upgrade_building("building_a")


def test_upgrade_rejected_when_maxed() -> None:
    village = _village(resources={RELIC: 2})
    village.upgrade_building("building_a")
    with pytest.raises(VillageError, match="already maxed"):
        village.upgrade_building("building_a")


def test_upgrade_rejected_by_town_level() -> None:
    # Town level 1 gates tier index 2+; our building's next tier is index 1
    # which is allowed. Build a 3-tier building to test the gate.
    doc = {
        "id": "tall",
        "name": "Tall",
        "tiers": [
            {"cost": {}, "unlocks": [], "visual": "plot"},
            {"cost": {"relics": 1}, "unlocks": [], "visual": "tier1"},
            {"cost": {"relics": 2}, "unlocks": [], "visual": "tier2"},
        ],
    }
    village = VillageState.from_registry_documents([doc])
    village.resources = {RELIC: 10}
    village.upgrade_building("tall")  # tier 1: town_level 1 >= 1 OK
    with pytest.raises(VillageError, match="town level"):
        village.upgrade_building("tall")  # tier 2 needs town level 2


# -- Visual state mapping --

def test_visual_state_follows_tier() -> None:
    village = _village(resources={RELIC: 1})
    assert village.get_building("building_a").visual_state == "plot"
    village.upgrade_building("building_a")
    assert village.get_building("building_a").visual_state == "tier1"


def test_earned_unlocks_accumulate_across_tiers() -> None:
    doc = {
        "id": "multi",
        "name": "Multi",
        "tiers": [
            {"cost": {}, "unlocks": ["unlock_zero"], "visual": "plot"},
            {"cost": {"relics": 1}, "unlocks": ["unlock_one"], "visual": "tier1"},
        ],
    }
    village = VillageState.from_registry_documents([doc])
    village.resources = {RELIC: 1}
    assert village.earned_unlocks() == ("unlock_zero",)
    village.upgrade_building("multi")
    assert set(village.earned_unlocks()) == {"unlock_zero", "unlock_one"}


# -- Run results --

def test_run_result_banks_gold() -> None:
    village = _village()
    village.apply_run_result(_FakeRunResult(gold_earned=120))
    assert village.resources[GOLD] == 120


def test_boss_victory_grants_relic() -> None:
    village = _village()
    village.apply_run_result(_FakeRunResult(victory=True, gold_earned=80))
    assert village.resources[RELIC] == 1
    assert village.resources[GOLD] == 80


def test_death_run_banks_gold_without_relic() -> None:
    village = _village()
    village.apply_run_result(_FakeRunResult(victory=False, gold_earned=30))
    assert village.resources[GOLD] == 30
    assert village.resources[RELIC] == 0


# -- Persistence roundtrip --

def test_village_state_roundtrip() -> None:
    village = _village(resources={RELIC: 1})
    village.upgrade_building("building_a")
    village.town_level = 3
    village.add_resources({GOLD: 50})

    payload = village.to_state()
    restored = VillageState.from_registry_documents([BUILDING_A], payload)

    assert restored.town_level == 3
    assert restored.resources[RELIC] == 0  # spent on the upgrade
    assert restored.resources[GOLD] == 50
    assert restored.building_tier("building_a") == 1
    assert restored.get_building("building_a").visual_state == "tier1"


def test_village_state_roundtrip_with_missing_save() -> None:
    """A fresh save (no state) must produce a default village."""
    village = VillageState.from_registry_documents([BUILDING_A])
    assert village.town_level == 1
    assert village.building_tier("building_a") == 0
    assert village.resources == {GOLD: 0, RELIC: 0}


def test_village_rejects_unknown_building() -> None:
    village = _village()
    with pytest.raises(VillageError, match="unknown building"):
        village.get_building("nope")
