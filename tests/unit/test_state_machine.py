"""Tests for core.state_machine (infrastructure only)."""

from __future__ import annotations

import pytest

from core.state_machine import State, StateMachine


def _machine() -> tuple[StateMachine, list[str]]:
    calls: list[str] = []
    machine = StateMachine()
    machine.add_state(
        State(
            "idle",
            on_enter=lambda: calls.append("enter_idle"),
            on_exit=lambda: calls.append("exit_idle"),
        )
    )
    machine.add_state(State("run", on_enter=lambda: calls.append("enter_run")))
    return machine, calls


def test_initial_state_is_none() -> None:
    machine, _ = _machine()
    assert machine.current is None


def test_transitions_fire_hooks() -> None:
    machine, calls = _machine()
    machine.set_state("idle")
    machine.set_state("run")
    assert calls == ["enter_idle", "exit_idle", "enter_run"]
    assert machine.current == "run"


def test_unknown_state_raises() -> None:
    machine, _ = _machine()
    with pytest.raises(KeyError):
        machine.set_state("fly")


def test_disallowed_transition_raises() -> None:
    machine = StateMachine(allowed_transitions={"idle": {"run"}})
    machine.add_state(State("idle"))
    machine.add_state(State("run"))
    machine.add_state(State("jump"))
    machine.set_state("idle")
    with pytest.raises(ValueError):
        machine.set_state("jump")


def test_duplicate_state_raises() -> None:
    machine, _ = _machine()
    with pytest.raises(ValueError):
        machine.add_state(State("idle"))
