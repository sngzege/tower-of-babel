"""Run checkpoint: mid-run save payload (Phase 14, D15 provisional policy).

D15 provisional default (RULES.md §0): save at village + run checkpoint at
room transitions; quit-to-menu saves the run checkpoint. This module defines
the *payload* (plain dict) for an in-progress run and how to validate it.

A checkpoint captures only what the run system owns (ARCHITECTURE.md §6):
run phase, floor/room position, player health, and the BuildState. It is a
plain-data snapshot; the save manager never interprets it. Restoring a
checkpoint is the scene's job (it owns the player/camera/stage objects).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gameplay.builds.build_state import BuildState

CHECKPOINT_VERSION = 1

REQUIRED_KEYS: tuple[str, ...] = (
    "version",
    "phase",
    "floor_index",
    "room_id",
    "player_health",
    "build",
)


def build_checkpoint(
    *,
    phase: str,
    floor_index: int,
    room_id: str,
    player_health: float,
    build: BuildState,
) -> dict[str, Any]:
    """Serialize one run checkpoint."""
    return {
        "version": CHECKPOINT_VERSION,
        "phase": phase,
        "floor_index": int(floor_index),
        "room_id": str(room_id),
        "player_health": float(player_health),
        "build": build.to_state(),
    }


def validate_checkpoint(payload: object) -> list[str]:
    """Structural validation of a run checkpoint payload."""
    problems: list[str] = []
    if not isinstance(payload, dict):
        return ["run checkpoint is not a mapping"]
    for key in REQUIRED_KEYS:
        if key not in payload:
            problems.append(f"run checkpoint missing '{key}'")
    if payload.get("version") != CHECKPOINT_VERSION:
        problems.append(
            f"run checkpoint version {payload.get('version')} != {CHECKPOINT_VERSION}"
        )
    if "build" in payload and not isinstance(payload["build"], dict):
        problems.append("run checkpoint 'build' is not a mapping")
    if "player_health" in payload and not isinstance(
        payload["player_health"], (int, float)
    ):
        problems.append("run checkpoint 'player_health' is not a number")
    return problems


@dataclass(frozen=True)
class RunCheckpoint:
    """Validated run checkpoint snapshot (restored by the dungeon scene)."""

    phase: str
    floor_index: int
    room_id: str
    player_health: float
    build: BuildState

    @classmethod
    def from_payload(cls, payload: object) -> RunCheckpoint:
        problems = validate_checkpoint(payload)
        if problems:
            raise ValueError("invalid run checkpoint: " + "; ".join(problems))
        assert isinstance(payload, dict)
        build_payload = payload.get("build", {})
        assert isinstance(build_payload, dict)
        return cls(
            phase=str(payload.get("phase", "")),
            floor_index=int(payload.get("floor_index", 0)),
            room_id=str(payload.get("room_id", "")),
            player_health=float(payload.get("player_health", 0.0)),
            build=BuildState.state_from(build_payload),
        )
