"""Seeded random-number utilities.

Wraps :class:`random.Random` so every system can receive its own stream derived
from a run seed (reproducible runs; see IMPLEMENTATION_PLAN seed support).
Infrastructure only - no gameplay logic.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")


class Rng:
    """A small explicit wrapper around random.Random."""

    def __init__(self, seed: int | str) -> None:
        self.seed = seed
        self._random = random.Random(seed)

    def fork(self, salt: int | str) -> Rng:
        """Derive a deterministic child stream (e.g. per-floor or per-room)."""
        return Rng(f"{self.seed}:{salt}")

    def int_range(self, minimum: int, maximum: int) -> int:
        return self._random.randint(minimum, maximum)

    def chance(self, probability: float) -> bool:
        return self._random.random() < probability

    def choice(self, items: Sequence[T]) -> T:
        return self._random.choice(items)

    def shuffle(self, items: list[T]) -> list[T]:
        self._random.shuffle(items)
        return items

    def weighted_choice(self, items: Sequence[T], weights: Sequence[float]) -> T:
        if len(items) != len(weights):
            raise ValueError("items and weights must have equal length")
        if not items:
            raise ValueError("cannot choose from an empty sequence")
        return self._random.choices(items, weights=weights, k=1)[0]
