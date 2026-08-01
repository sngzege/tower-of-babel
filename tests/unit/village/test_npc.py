"""Phase 12 tests: NPC Framework.

Verifies:
  - NPC loads from data documents (service tier levels, dialogue, arrival)
  - Milestone arrival: first boss kill marks NPCs as arrived
  - Service tier progression changes service options
  - Dialogue data plumbing
  - Persistence roundtrip
"""

from __future__ import annotations

import pytest

from gameplay.village.npc import NPC, NPCError, NPCService

NPC_A = {
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
    "dialogue": {"greeting": "NPC A greets you."},
}

NPC_B = {
    "id": "npc_b",
    "name": "NPC B",
    "service": "run_prep",
    "building_id": "building_b",
    "arrival": {"trigger": "first_boss_kill"},
    "tracks": {
        "service_tier": {
            "levels": [
                {"requires_milestone": "", "unlocks": []},
                {"requires_milestone": "first_boss_kill", "unlocks": ["service_run_prep_tier1"]},
            ]
        }
    },
    "dialogue": {"greeting": "NPC B greets you."},
}

MILESTONE = frozenset({"first_boss_kill"})


def _service(*docs: dict) -> NPCService:
    return NPCService.from_registry_documents(list(docs))


# -- Document parsing --

def test_npc_loads_from_document() -> None:
    npc = NPC.from_document(NPC_A)
    assert npc.npc_id == "npc_a"
    assert npc.service == "loadout"
    assert npc.building_id == "building_a"
    assert npc.arrival_trigger == "first_boss_kill"
    assert not npc.arrived
    assert npc.service_tier == 0
    assert npc.dialogue["greeting"] == "NPC A greets you."


def test_npc_requires_arrival_trigger() -> None:
    with pytest.raises(NPCError, match="arrival.trigger"):
        NPC.from_document({"id": "bad", "name": "Bad", "arrival": {}})


def test_npc_dialogue_line_lookup() -> None:
    npc = NPC.from_document(NPC_A)
    assert npc.dialogue_line("greeting") == "NPC A greets you."
    assert npc.dialogue_line("missing", default="...") == "..."


# -- Milestone arrival --

def test_npc_arrives_after_boss_kill() -> None:
    service = _service(NPC_A)
    assert not service.get("npc_a").arrived
    newly = service.reconcile_arrivals(frozenset())
    assert newly == 0
    assert not service.get("npc_a").arrived

    newly = service.reconcile_arrivals(MILESTONE)
    assert newly == 1
    assert service.get("npc_a").arrived


def test_service_roster_counts_arrivals() -> None:
    service = _service(NPC_A, NPC_B)
    service.reconcile_arrivals(MILESTONE)
    assert {npc.npc_id for npc in service.arrived_npcs()} == {"npc_a", "npc_b"}


# -- Service tier progression --

def test_service_tier_advances_on_milestone() -> None:
    service = _service(NPC_A)
    # Before milestone: no options, tier 0.
    assert service.get("npc_a").service_options() == ()
    service.reconcile_arrivals(MILESTONE)
    service.reconcile_service_tiers(MILESTONE)
    npc = service.get("npc_a")
    assert npc.service_tier == 1
    assert npc.service_options() == ("service_loadout_tier1",)


def test_service_tier_does_not_advance_without_milestone() -> None:
    service = _service(NPC_A)
    service.reconcile_arrivals(MILESTONE)
    advanced = service.reconcile_service_tiers(frozenset())
    assert advanced == 0
    assert service.get("npc_a").service_tier == 0


def test_service_tier_unlocks_new_option() -> None:
    """Acceptance: a service tier unlocks a new option."""
    service = _service(NPC_B)
    service.reconcile_arrivals(MILESTONE)
    service.reconcile_service_tiers(MILESTONE)
    options = service.get("npc_b").service_options()
    assert "service_run_prep_tier1" in options


# -- Persistence roundtrip --

def test_npc_state_roundtrip() -> None:
    service = _service(NPC_A, NPC_B)
    service.reconcile_arrivals(MILESTONE)
    service.reconcile_service_tiers(MILESTONE)

    payload = service.to_state()
    restored = NPCService.from_registry_documents([NPC_A, NPC_B], payload)

    assert restored.get("npc_a").arrived
    assert restored.get("npc_a").service_tier == 1
    assert restored.get("npc_b").arrived
    assert restored.get("npc_b").service_tier == 1


def test_npc_state_fresh_default() -> None:
    service = NPCService.from_registry_documents([NPC_A])
    assert not service.get("npc_a").arrived
    assert service.get("npc_a").service_tier == 0
