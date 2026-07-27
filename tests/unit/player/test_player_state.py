"""Tests for gameplay.player.player_state: the player state machine (Phase 3)."""

from __future__ import annotations

import pytest

from gameplay.player.player_state import (
    ALLOWED_TRANSITIONS,
    PlayerState,
    build_player_state_machine,
)


def test_machine_starts_idle() -> None:
    machine = build_player_state_machine()
    assert machine.current == PlayerState.IDLE.value


def test_every_state_is_registered() -> None:
    machine = build_player_state_machine()
    for state in PlayerState:
        assert state.value in machine._states  # noqa: SLF001


def test_core_gameplay_transitions_are_legal() -> None:
    machine = build_player_state_machine()
    machine.set_state(PlayerState.MOVE.value)
    machine.set_state(PlayerState.DODGE.value)
    machine.set_state(PlayerState.MOVE.value)
    machine.set_state(PlayerState.IDLE.value)
    assert machine.current == PlayerState.IDLE.value


def test_placeholder_states_are_reachable_for_combat() -> None:
    """HIT and DEAD (Phase 4 behavior) must already be wired (Phase 3 spec)."""
    machine = build_player_state_machine()
    machine.set_state(PlayerState.HIT.value)
    assert machine.current == PlayerState.HIT.value
    machine.set_state(PlayerState.DEAD.value)
    assert machine.current == PlayerState.DEAD.value


def test_illegal_transition_raises() -> None:
    machine = build_player_state_machine()
    with pytest.raises(ValueError, match="not allowed"):
        machine.set_state(PlayerState.IDLE.value)  # self-transition not listed


def test_dead_is_terminal() -> None:
    machine = build_player_state_machine()
    machine.set_state(PlayerState.DEAD.value)
    with pytest.raises(ValueError, match="not allowed"):
        machine.set_state(PlayerState.IDLE.value)


def test_transition_table_covers_live_states() -> None:
    """Dodge must be reachable from grounded states (the core defensive verb)."""
    assert PlayerState.DODGE in ALLOWED_TRANSITIONS[PlayerState.IDLE]
    assert PlayerState.DODGE in ALLOWED_TRANSITIONS[PlayerState.MOVE]
    assert PlayerState.DODGE not in ALLOWED_TRANSITIONS[PlayerState.DEAD]
