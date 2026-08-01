"""Phase 13 tests: Persistent Progression.

Verifies:
  - Class mastery: XP gain, level ups, milestone bonuses (L13)
  - Unlock engine: milestone-driven grants into reward pools
  - Records: best depth, victories, run counting
  - Run-start bonuses applied to a fresh BuildState (L15)
  - Persistence roundtrip
"""

from __future__ import annotations

import pytest

from gameplay.builds.build_state import BuildState
from gameplay.progression.mastery import ClassMastery, MasteryState
from gameplay.progression.meta_progression import (
    RECORD_BEST_DEPTH,
    RECORD_RUNS,
    RECORD_VICTORIES,
    MetaProgression,
)
from gameplay.progression.unlocks import UnlockEngine

MASTERY_DOC = {
    "id": "warrior_mastery",
    "kind": "mastery",
    "class_id": "warrior",
    "xp_per_level": 100,
    "bonuses": [
        {"at_level": 2, "stat": "max_health", "value": 10, "is_percent": False},
        {"at_level": 3, "stat": "damage", "value": 0.05, "is_percent": True},
    ],
}

UNLOCK_DOC = {
    "id": "unlock_first_boss",
    "name": "First Boss Reward",
    "kind": "boon_pool",
    "source": "first_boss_kill",
    "requires": [],
    "grants": ["boon_weapon_damage"],
}

UNLOCK_CHAIN_A = {
    "id": "unlock_chain_a",
    "name": "Chain A",
    "kind": "boon_pool",
    "source": "first_boss_kill",
    "grants": ["boon_a"],
}
UNLOCK_CHAIN_B = {
    "id": "unlock_chain_b",
    "name": "Chain B",
    "kind": "boon_pool",
    "source": "",
    "requires": ["unlock_chain_a"],
    "grants": ["boon_b"],
}


class _FakeRunResult:
    def __init__(self, *, victory: bool = False, depth_reached: int = 1) -> None:
        self.victory = victory
        self.depth_reached = depth_reached


def _meta() -> MetaProgression:
    return MetaProgression.from_documents([MASTERY_DOC], [UNLOCK_DOC])


# -- Mastery --

def test_mastery_xp_levels_up() -> None:
    curve = ClassMastery.from_document(MASTERY_DOC)
    state = MasteryState()
    gained = state.add_xp(curve, 250)
    assert gained == 2  # 100 + 100, remainder 50
    assert state.level == 3
    assert state.xp == 50


def test_mastery_bonuses_at_level() -> None:
    meta = _meta()
    meta.grant_xp("warrior", 250)  # level 3
    bonuses = meta.mastery_bonuses("warrior")
    assert {b.stat for b in bonuses} == {"max_health", "damage"}


def test_mastery_level_query() -> None:
    meta = _meta()
    assert meta.mastery_level("warrior") == 1
    meta.grant_xp("warrior", 150)
    assert meta.mastery_level("warrior") == 2


def test_mastery_ignores_unknown_class_curve() -> None:
    meta = _meta()
    assert meta.grant_xp("ranger", 500) == 0  # no curve registered


# -- Unlock engine --

def test_unlock_earned_after_milestone() -> None:
    engine = UnlockEngine.from_registry_documents([UNLOCK_DOC])
    assert engine.earned_ids(frozenset()) == frozenset()
    earned = engine.earned_ids(frozenset({"first_boss_kill"}))
    assert earned == frozenset({"unlock_first_boss"})
    assert engine.granted_ids(frozenset({"first_boss_kill"})) == frozenset(
        {"boon_weapon_damage"}
    )


def test_unlock_grants_by_kind() -> None:
    engine = UnlockEngine.from_registry_documents([UNLOCK_DOC])
    grants = engine.granted_by_kind(frozenset({"first_boss_kill"}), "boon_pool")
    assert grants == ("boon_weapon_damage",)


def test_unlock_prerequisite_chain() -> None:
    engine = UnlockEngine.from_registry_documents([UNLOCK_CHAIN_A, UNLOCK_CHAIN_B])
    # Milestone alone unlocks chain A, whose grant satisfies B's prerequisite.
    earned = engine.earned_ids(frozenset({"first_boss_kill"}))
    assert earned == frozenset({"unlock_chain_a", "unlock_chain_b"})
    assert engine.granted_ids(frozenset({"first_boss_kill"})) == frozenset(
        {"boon_a", "boon_b"}
    )


# -- Records --

def test_victory_updates_records_and_milestone() -> None:
    meta = _meta()
    meta.record_run_result(_FakeRunResult(victory=True, depth_reached=5))
    assert meta.records[RECORD_RUNS] == 1
    assert meta.records[RECORD_VICTORIES] == 1
    assert meta.records[RECORD_BEST_DEPTH] == 5
    assert meta.has_milestone("first_boss_kill")
    assert "boon_weapon_damage" in meta.granted_boons()


def test_death_updates_run_count_without_victory() -> None:
    meta = _meta()
    meta.record_run_result(_FakeRunResult(victory=False, depth_reached=2))
    meta.record_run_result(_FakeRunResult(victory=False, depth_reached=4))
    assert meta.records[RECORD_RUNS] == 2
    assert meta.records[RECORD_VICTORIES] == 0
    assert meta.records[RECORD_BEST_DEPTH] == 4
    assert not meta.has_milestone("first_boss_kill")


def test_best_depth_never_decreases() -> None:
    meta = _meta()
    meta.record_run_result(_FakeRunResult(victory=False, depth_reached=3))
    meta.record_run_result(_FakeRunResult(victory=False, depth_reached=1))
    assert meta.best_depth() == 3


# -- Run-start bonuses (L15) --

def test_run_start_bonuses_apply_to_build() -> None:
    meta = _meta()
    meta.grant_xp("warrior", 250)  # level 3 -> max_health +10, damage +5%
    build = BuildState()
    base_damage = 50.0
    meta.apply_run_start_bonuses(build, class_id="warrior")
    assert build.max_health_bonus == 10
    assert build.total_damage_for(base_damage, frozenset()) == pytest.approx(52.5)


def test_run_start_bonuses_noop_for_fresh_save() -> None:
    meta = _meta()  # level 1: no bonuses yet
    build = BuildState()
    meta.apply_run_start_bonuses(build)
    assert build.max_health_bonus == 0
    assert build.total_damage_for(50.0, frozenset()) == 50.0


# -- Persistence roundtrip --

def test_meta_progression_roundtrip() -> None:
    meta = _meta()
    meta.grant_xp("warrior", 150)
    meta.record_run_result(_FakeRunResult(victory=True, depth_reached=4))

    payload = meta.to_state()
    restored = MetaProgression.from_documents([MASTERY_DOC], [UNLOCK_DOC], payload)

    assert restored.mastery_level("warrior") == 2
    assert restored.has_milestone("first_boss_kill")
    assert restored.records[RECORD_VICTORIES] == 1
    assert restored.records[RECORD_BEST_DEPTH] == 4
    assert restored.granted_boons() == ("boon_weapon_damage",)


def test_meta_progression_fresh_default() -> None:
    meta = MetaProgression.from_documents([MASTERY_DOC], [UNLOCK_DOC])
    assert meta.mastery_level("warrior") == 1
    assert not meta.has_milestone("first_boss_kill")
    assert meta.best_depth() == 0
    assert meta.granted_boons() == ()
