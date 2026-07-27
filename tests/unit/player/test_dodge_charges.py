"""Tests for dodge_charges.DodgeCharges: standalone, framework-free (Phase 3.5)."""

from __future__ import annotations

import pytest

from gameplay.player.dodge_charges import DodgeCharges

COOLDOWN = 1.5
MAX = 2


def test_starts_with_max_charges() -> None:
    dc = DodgeCharges(max_charges=MAX, cooldown=COOLDOWN)
    assert dc.current == MAX
    assert dc.ready


def test_first_dodge_consumes_one() -> None:
    dc = DodgeCharges(max_charges=MAX, cooldown=COOLDOWN)
    assert dc.consume()
    assert dc.current == MAX - 1


def test_second_consecutive_dodge_consumes_second() -> None:
    dc = DodgeCharges(max_charges=MAX, cooldown=COOLDOWN)
    dc.consume()
    dc.consume()
    assert dc.current == 0
    assert not dc.ready


def test_third_dodge_rejected_when_empty() -> None:
    dc = DodgeCharges(max_charges=MAX, cooldown=COOLDOWN)
    dc.consume()
    dc.consume()
    assert not dc.consume()
    assert dc.current == 0


def test_one_charge_regenerates_after_cooldown() -> None:
    dc = DodgeCharges(max_charges=MAX, cooldown=COOLDOWN)
    dc.consume()
    dc.update(COOLDOWN)
    assert dc.current == MAX  # charge regenerated -> full again
    assert dc.consume()


def test_two_charges_regenerate_independently() -> None:
    dc = DodgeCharges(max_charges=MAX, cooldown=COOLDOWN)
    dc.consume()  # slot 0 starts at 0.0
    dc.update(0.8)  # slot 0 elapsed=0.8, not full yet
    dc.consume()  # slot 1 starts at 0.0
    dc.update(0.7)  # total 1.5 from first: slot 0 elapsed=1.5 (full)
                     # slot 1 elapsed=0.7 (still recharging)
    assert dc.current == 1
    dc.update(0.8)  # slot 1 elapsed=1.5
    assert dc.current == MAX


def test_charges_never_exceed_max() -> None:
    dc = DodgeCharges(max_charges=MAX, cooldown=COOLDOWN)
    dc.update(COOLDOWN * 10)
    assert dc.current == MAX
    for progress in dc.charges:
        assert progress <= COOLDOWN


def test_cooldown_does_not_accumulate_above_capacity() -> None:
    dc = DodgeCharges(max_charges=MAX, cooldown=COOLDOWN)
    dc.consume()
    dc.update(COOLDOWN * 10)
    assert dc.current == MAX


def test_reset_restores_two() -> None:
    dc = DodgeCharges(max_charges=MAX, cooldown=COOLDOWN)
    dc.consume()
    dc.consume()
    assert dc.current == 0
    dc.reset()
    assert dc.current == MAX


def test_iframes_independent_of_charge_regen() -> None:
    dc = DodgeCharges(max_charges=MAX, cooldown=COOLDOWN)
    # Update charges while full: progress stays at cooldown cap.
    dc.update(0.5)
    for progress in dc.charges:
        assert progress == COOLDOWN


def test_invalid_constructor_raises() -> None:
    with pytest.raises(ValueError, match="max_charges"):
        DodgeCharges(max_charges=0, cooldown=COOLDOWN)
    with pytest.raises(ValueError, match="cooldown"):
        DodgeCharges(max_charges=MAX, cooldown=0.0)
