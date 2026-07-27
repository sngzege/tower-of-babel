"""Player state machine vocabulary (Phase 3).

IDLE, MOVE, and DODGE are live states. HIT and DEAD are deliberate
placeholders (Phase 3 spec): they exist so the transition table and the
animation hooks are settled now; combat (Phase 4) fills in their behavior.
Built on core.state_machine with an explicit transition table - illegal
transitions raise instead of silently corrupting gameplay state.
"""

from __future__ import annotations

from enum import Enum

from core.state_machine import State, StateMachine


class PlayerState(Enum):
    """Top-level player states (drives logic AND animation hooks)."""

    IDLE = "idle"
    MOVE = "move"
    DODGE = "dodge"
    HIT = "hit"  # placeholder: hit-stun arrives with combat (Phase 4)
    DEAD = "dead"  # placeholder: death handling arrives with combat (Phase 4)


ALLOWED_TRANSITIONS: dict[PlayerState, frozenset[PlayerState]] = {
    PlayerState.IDLE: frozenset(
        {PlayerState.MOVE, PlayerState.DODGE, PlayerState.HIT, PlayerState.DEAD}
    ),
    PlayerState.MOVE: frozenset(
        {PlayerState.IDLE, PlayerState.DODGE, PlayerState.HIT, PlayerState.DEAD}
    ),
    PlayerState.DODGE: frozenset(
        {PlayerState.IDLE, PlayerState.MOVE, PlayerState.HIT, PlayerState.DEAD}
    ),
    PlayerState.HIT: frozenset(
        {PlayerState.IDLE, PlayerState.MOVE, PlayerState.DEAD}
    ),
    PlayerState.DEAD: frozenset(),
}


def build_player_state_machine(
    initial: PlayerState = PlayerState.IDLE,
) -> StateMachine:
    """A core StateMachine preloaded with the player states and rules."""
    machine = StateMachine(
        allowed_transitions={
            state.value: {target.value for target in targets}
            for state, targets in ALLOWED_TRANSITIONS.items()
        }
    )
    for state in PlayerState:
        machine.add_state(State(state.value))
    machine.set_state(initial.value)
    return machine
