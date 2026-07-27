"""Tests for utils.random_utils (infrastructure only)."""

from __future__ import annotations

import pytest

from utils.random_utils import Rng


def test_same_seed_same_sequence() -> None:
    assert Rng("seed").int_range(0, 1000) == Rng("seed").int_range(0, 1000)


def test_fork_is_deterministic_and_distinct() -> None:
    a = Rng("seed").fork("floor-1").int_range(0, 1000)
    b = Rng("seed").fork("floor-1").int_range(0, 1000)
    c = Rng("seed").fork("floor-2").int_range(0, 1000)
    assert a == b
    assert a != c


def test_weighted_choice_respects_zero_weight() -> None:
    rng = Rng(1)
    for _ in range(50):
        assert rng.weighted_choice(["a", "b"], [1.0, 0.0]) == "a"


def test_weighted_choice_validation() -> None:
    rng = Rng(1)
    with pytest.raises(ValueError):
        rng.weighted_choice([], [])
    with pytest.raises(ValueError):
        rng.weighted_choice(["a"], [1.0, 2.0])
