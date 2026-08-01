"""Phase 14 tests: Save/Load Integration.

Verifies:
  - BuildState checkpoint serialization roundtrip
  - RunCheckpoint payload validation + restore
  - PersistentState full roundtrip through the save manager (village + npcs
    + progression under save['persistent'])
  - Corrupted save handling (bad YAML, structural damage, bad run_state)
  - Slot management (multiple slots, occupied detection)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gameplay.builds.build_state import BuildState
from gameplay.persistent_state import PersistentState
from gameplay.run_checkpoint import (
    RunCheckpoint,
    build_checkpoint,
    validate_checkpoint,
)
from gameplay.village.village import RELIC
from save.save_manager import SaveError, SaveManager
from save.save_schema import new_save_template
from save.save_slots import SlotManager

MASTERY_DOC = {
    "id": "warrior_mastery",
    "kind": "mastery",
    "class_id": "warrior",
    "xp_per_level": 100,
    "bonuses": [{"at_level": 2, "stat": "max_health", "value": 10, "is_percent": False}],
}
UNLOCK_DOC = {
    "id": "unlock_first_boss",
    "name": "First Boss Reward",
    "kind": "boon_pool",
    "source": "first_boss_kill",
    "grants": ["boon_weapon_damage"],
}
BUILDING_DOC = {
    "id": "building_a",
    "name": "Workshop A",
    "service": "loadout",
    "plot": "plot_north",
    "tiers": [
        {"cost": {}, "unlocks": [], "visual": "plot"},
        {"cost": {"relics": 1}, "unlocks": [], "visual": "tier1"},
    ],
}
NPC_DOC = {
    "id": "npc_a",
    "name": "NPC A",
    "service": "loadout",
    "building_id": "building_a",
    "arrival": {"trigger": "first_boss_kill"},
    "tracks": {
        "service_tier": {
            "levels": [
                {"requires_milestone": "", "unlocks": []},
                {"requires_milestone": "first_boss_kill", "unlocks": ["service_loadout_tier1"]},
            ]
        }
    },
    "dialogue": {"greeting": "hi"},
}


class _FakeRunResult:
    def __init__(self, *, victory: bool = False, depth_reached: int = 1) -> None:
        self.victory = victory
        self.depth_reached = depth_reached
        self.gold_earned = 0
        self.relics_earned = 0


def _persistent() -> PersistentState:
    return PersistentState.from_save(
        village_documents=[BUILDING_DOC],
        npc_documents=[NPC_DOC],
        mastery_documents=[MASTERY_DOC],
        unlock_documents=[UNLOCK_DOC],
    )


# -- BuildState checkpoint roundtrip --

def test_build_state_roundtrip() -> None:
    build = BuildState()
    build.weapon_id = "warrior_spear"
    build.ability_ids.extend(["warrior_charge", "warrior_whirlwind"])
    build.passive_ids.append("hardy")
    build.boon_ids.append("boon_damage_up")
    build.add_weapon_upgrade("damage", 0.2)

    restored = BuildState.state_from(build.to_state())
    assert restored.weapon_id == "warrior_spear"
    assert restored.ability_ids == ["warrior_charge", "warrior_whirlwind"]
    assert restored.passive_ids == ["hardy"]
    assert restored.boon_ids == ["boon_damage_up"]
    assert restored.get_weapon_upgrade("damage") == pytest.approx(0.2)


# -- RunCheckpoint --

def test_checkpoint_roundtrip() -> None:
    build = BuildState()
    build.weapon_id = "warrior_axe"
    payload = build_checkpoint(
        phase="boss",
        floor_index=4,
        room_id="boss_arena",
        player_health=63.0,
        build=build,
    )
    assert validate_checkpoint(payload) == []
    cp = RunCheckpoint.from_payload(payload)
    assert cp.phase == "boss"
    assert cp.floor_index == 4
    assert cp.room_id == "boss_arena"
    assert cp.player_health == 63.0
    assert cp.build.weapon_id == "warrior_axe"


def test_checkpoint_rejects_bad_payload() -> None:
    problems = validate_checkpoint({"version": 99})
    assert problems  # missing keys + wrong version
    with pytest.raises(ValueError, match="invalid run checkpoint"):
        RunCheckpoint.from_payload({"version": 99})


# -- PersistentState full roundtrip --

def test_persistent_state_roundtrip_through_save_manager(tmp_path: Path) -> None:
    persistent = _persistent()
    # Evolve state: spend relic on building, boss kill -> milestones/NPCs.
    persistent.village.resources = {RELIC: 1}
    persistent.village.upgrade_building("building_a")
    persistent.apply_run_result(_FakeRunResult(victory=True, depth_reached=5))

    manager = SaveManager(path=tmp_path / "save.yaml")
    save = new_save_template()
    save["persistent"] = persistent.to_save()
    save["run_state"] = build_checkpoint(
        phase="active", floor_index=2, room_id="room_7", player_health=40.0,
        build=BuildState.state_from({"weapon_id": "warrior_spear"}),
    )
    manager.write(save)

    loaded = manager.read()
    assert loaded["run_state"] is not None
    assert loaded["run_state"]["phase"] == "active"

    restored = PersistentState.from_save(
        village_documents=[BUILDING_DOC],
        npc_documents=[NPC_DOC],
        mastery_documents=[MASTERY_DOC],
        unlock_documents=[UNLOCK_DOC],
        saved_persistent=loaded["persistent"],
    )
    # Village state survived: tier upgraded; the victory re-banked 1 relic
    # (provisional boss reward) after the upgrade spent the first one.
    assert restored.village.building_tier("building_a") == 1
    assert restored.village.resources[RELIC] == 1
    # Progression survived (boss kill recorded).
    assert restored.progression.has_milestone("first_boss_kill")
    assert restored.progression.best_depth() == 5
    assert "boon_weapon_damage" in restored.progression.granted_boons()
    # NPCs arrived + advanced after the milestone.
    assert restored.npcs.get("npc_a").arrived
    assert restored.npcs.get("npc_a").service_tier == 1

    # Run checkpoint survived.
    cp = RunCheckpoint.from_payload(loaded["run_state"])
    assert cp.floor_index == 2
    assert cp.build.weapon_id == "warrior_spear"


# -- Corrupted save handling --

def test_corrupted_yaml_raises_save_error(tmp_path: Path) -> None:
    path = tmp_path / "save.yaml"
    path.write_text("not: [valid: yaml", encoding="utf-8")
    manager = SaveManager(path=path)
    with pytest.raises(SaveError):
        manager.read()


def test_corrupted_structure_raises_save_error(tmp_path: Path) -> None:
    path = tmp_path / "save.yaml"
    path.write_text("meta: {}\n", encoding="utf-8")  # missing persistent/run_state
    manager = SaveManager(path=path)
    with pytest.raises(SaveError, match="structural validation"):
        manager.read()


def test_corrupted_run_state_is_rejected_on_restore(tmp_path: Path) -> None:
    manager = SaveManager(path=tmp_path / "save.yaml")
    save = new_save_template()
    save["run_state"] = {"garbage": True}
    manager.write(save)
    loaded = manager.read()
    problems = validate_checkpoint(loaded["run_state"])
    assert problems  # refuses to restore a garbage checkpoint


# -- Slot management --

def test_slot_manager_multiple_slots(tmp_path: Path) -> None:
    slots = SlotManager(saves_dir=tmp_path, slot_count=3)
    assert slots.exists(0) is False
    slots.write(0, new_save_template())
    slots.write(2, new_save_template())
    assert slots.exists(0)
    assert slots.exists(1) is False
    assert slots.exists(2)
    assert slots.occupied_slots() == [0, 2]
    assert slots.read(0)["run_state"] is None


def test_slot_manager_out_of_range(tmp_path: Path) -> None:
    slots = SlotManager(saves_dir=tmp_path, slot_count=2)
    with pytest.raises(IndexError):
        slots.manager(5)


def test_slot_manager_delete(tmp_path: Path) -> None:
    slots = SlotManager(saves_dir=tmp_path, slot_count=2)
    slots.write(0, new_save_template())
    assert slots.exists(0)
    slots.delete(0)
    assert not slots.exists(0)
