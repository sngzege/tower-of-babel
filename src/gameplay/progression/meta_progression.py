"""Meta progression: persistent cross-run progression (L11/L13/L15).

Owns the persistent side of progression:
  - per-class mastery progress (MasteryState per class, L13)
  - earned milestones (boss first-kills, depth records, ...)
  - run records (best depth, victories, total runs)
  - run-start bonus application (L15: every run begins with permanent
    bonuses applied)

Everything is behind plain-data interfaces so the save system can serialize
it (Phase 14) and the run system can read it without coupling. The class
mastery *curves* come from data (ClassMastery); the *progress* lives here.

Greybox scope (RULES.md §0): Warrior curve placeholder, one unlock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gameplay.progression.mastery import ClassMastery, MasteryState
from gameplay.progression.unlocks import MilestoneSet, UnlockEngine

# Record keys (provisional vocabulary, developer-owned).
RECORD_BEST_DEPTH = "best_depth"
RECORD_VICTORIES = "victories"
RECORD_RUNS = "total_runs"


@dataclass
class MetaProgression:
    """Persistent cross-run progression state."""

    mastery_states: dict[str, MasteryState] = field(default_factory=dict)
    milestones: set[str] = field(default_factory=set)
    records: dict[str, int] = field(default_factory=dict)

    # Curves + unlock engine are injected (data-owned), not persisted.
    curves: dict[str, ClassMastery] = field(default_factory=dict)
    unlock_engine: UnlockEngine = field(default_factory=UnlockEngine)

    # -- Construction --

    @classmethod
    def from_documents(
        cls,
        mastery_documents: list[dict[str, Any]],
        unlock_documents: list[dict[str, Any]],
        saved_state: dict[str, Any] | None = None,
    ) -> MetaProgression:
        curves = {
            str(doc.get("class_id", "")): ClassMastery.from_document(doc)
            for doc in mastery_documents
        }
        saved = saved_state or {}
        mastery_states = {
            str(class_id): MasteryState.state_from(state)
            for class_id, state in (saved.get("mastery") or {}).items()
            if isinstance(state, dict)
        }
        return cls(
            mastery_states=mastery_states,
            milestones=set(saved.get("milestones") or []),
            records={
                str(k): int(v)
                for k, v in (saved.get("records") or {}).items()
            },
            curves=curves,
            unlock_engine=UnlockEngine.from_registry_documents(unlock_documents),
        )

    # -- Mastery --

    def ensure_mastery(self, class_id: str) -> MasteryState:
        if class_id not in self.mastery_states:
            self.mastery_states[class_id] = MasteryState()
        return self.mastery_states[class_id]

    def mastery_level(self, class_id: str) -> int:
        return self.ensure_mastery(class_id).level

    def grant_xp(self, class_id: str, amount: int) -> int:
        """Grant class XP; returns levels gained."""
        curve = self.curves.get(class_id)
        if curve is None:
            return 0
        return self.ensure_mastery(class_id).add_xp(curve, amount)

    def mastery_bonuses(self, class_id: str) -> tuple[Any, ...]:
        """Earned mastery bonuses for a class (L13 permanent passives)."""
        curve = self.curves.get(class_id)
        if curve is None:
            return ()
        return curve.bonuses_at_or_below(self.mastery_level(class_id))

    # -- Milestones --

    def record_milestone(self, milestone_id: str) -> bool:
        """Record a milestone; returns True when newly recorded."""
        if milestone_id in self.milestones:
            return False
        self.milestones.add(milestone_id)
        return True

    def has_milestone(self, milestone_id: str) -> bool:
        return milestone_id in self.milestones

    @property
    def milestone_set(self) -> MilestoneSet:
        return frozenset(self.milestones)

    # -- Unlocks --

    def granted_unlock_ids(self) -> frozenset[str]:
        return self.unlock_engine.granted_ids(self.milestone_set)

    def granted_boons(self) -> tuple[str, ...]:
        return self.unlock_engine.granted_by_kind(self.milestone_set, "boon_pool")

    # -- Records --

    def record_run_result(self, result: Any) -> None:
        """Update records from a finished run (duck-typed RunResult)."""
        # Always initialize record keys so consumers can read them safely.
        self.records.setdefault(RECORD_RUNS, 0)
        self.records.setdefault(RECORD_VICTORIES, 0)
        self.records.setdefault(RECORD_BEST_DEPTH, 0)
        self.records[RECORD_RUNS] += 1
        if bool(getattr(result, "victory", False)):
            self.records[RECORD_VICTORIES] += 1
            self.record_milestone("first_boss_kill")
        depth = int(getattr(result, "depth_reached", 0) or 0)
        self.records[RECORD_BEST_DEPTH] = max(
            self.records[RECORD_BEST_DEPTH], depth
        )

    def best_depth(self) -> int:
        return self.records.get(RECORD_BEST_DEPTH, 0)

    # -- Run-start bonuses (L15) --

    def apply_run_start_bonuses(self, build: Any, class_id: str = "warrior") -> None:
        """Apply permanent bonuses to a fresh run's BuildState (L15).

        Mastery bonuses (L13) are translated into BuildState modifiers so the
        run begins with them applied. Rule-agnostic: only stats BuildState
        understands are touched.
        """
        for bonus in self.mastery_bonuses(class_id):
            stat = bonus.stat
            value = float(bonus.value)
            if stat == "max_health":
                build.apply_passive_modifier("max_health", value, False)
            elif stat in ("damage", "move_speed", "attack_speed"):
                build.apply_passive_modifier(stat, value, bonus.is_percent)
            elif stat == "dodge_charges":
                build.apply_passive_modifier(stat, value, False)

    # -- Serialization --

    def to_state(self) -> dict[str, Any]:
        return {
            "mastery": {
                class_id: state.to_state()
                for class_id, state in self.mastery_states.items()
            },
            "milestones": sorted(self.milestones),
            "records": dict(self.records),
        }
