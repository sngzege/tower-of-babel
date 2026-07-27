"""Dodge charge system: a reusable cooldown-based charge manager.

Completely decoupled from Player: any entity capable of dodging uses
one of these. Exposes the full state a future UI needs (current, maximum,
progress per charge) without knowing about rendering or gameplay.
Architecture supports any number of charges per cooldown (data-driven).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChargeSlot:
    """One charge: either available (elapsed >= cooldown) or recharging."""

    elapsed: float = 0.0


class DodgeCharges:
    """Manages N charges with independent per-charge timers.

    Charges recharge in order (the most-depleted slot recharges first).
    ``max_charges`` and ``cooldown`` come from player stats (data-driven).
    """

    def __init__(self, max_charges: int, cooldown: float) -> None:
        if max_charges < 1:
            raise ValueError("max_charges must be >= 1")
        if cooldown <= 0.0:
            raise ValueError("cooldown must be positive")
        self.max_charges = max_charges
        self.cooldown = cooldown
        self._slots: list[ChargeSlot] = [
            ChargeSlot(elapsed=cooldown) for _ in range(max_charges)
        ]

    @property
    def current(self) -> int:
        """Number of charges currently available (>=0, <= max_charges)."""
        return sum(1 for slot in self._slots if slot.elapsed >= self.cooldown)

    @property
    def charges(self) -> tuple[float, ...]:
        """Per-charge elapsed progress 0..cooldown (for UI)."""
        return tuple(min(s.elapsed, self.cooldown) for s in self._slots)

    @property
    def ready(self) -> bool:
        """True if at least one charge can be consumed right now."""
        return self.current > 0

    def consume(self) -> bool:
        """Use one charge. Returns False if no charges are available."""
        for slot in self._slots:
            if slot.elapsed >= self.cooldown:
                slot.elapsed = 0.0
                return True
        return False

    def update(self, dt: float) -> None:
        """Advance timers by ``dt``. Never exceeds max per charge."""
        for slot in self._slots:
            if slot.elapsed < self.cooldown:
                slot.elapsed = min(slot.elapsed + dt, self.cooldown)

    def reset(self) -> None:
        """Restore all charges to full (death, new run)."""
        for slot in self._slots:
            slot.elapsed = self.cooldown

    def refill(self) -> None:
        """Alias for reset: instantly restore all charges."""
        self.reset()
