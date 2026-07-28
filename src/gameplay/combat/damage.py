"""Damage pipeline: typed damage instances, hit resolution, and application.

Damage types/tags are pure strings defined in data files. The pipeline:
  1. Create a DamageInstance (value, type tags, knockback, status tags)
  2. Run it through DamagePipeline.apply() which checks invulnerability,
     applies damage, and returns a DamageResult
  3. The caller updates the target's health and publishes events

This module is framework-free: no pygame, no rendering, no gameplay imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DamageInstance:
    """A single damage packet produced by a hitbox hitting a hurtbox.

    ``value`` is the raw damage number before any modifiers.
    ``types`` are damage-type tags (e.g. 'physical', 'magical', 'fire').
    ``source_layer`` is the CollisionLayer of the originating hitbox.
    ``knockback`` is the push direction/force applied to the target ((0,0)=none).
    ``status_tags`` are status effects to apply on hit.
    """
    value: float
    types: frozenset[str] = frozenset()
    source_layer: str = ""
    knockback: tuple[float, float] = (0.0, 0.0)
    status_tags: frozenset[str] = frozenset()


@dataclass(frozen=True)
class DamageResult:
    """Report of what happened when damage was applied.

    ``dealt`` is how much damage actually went through (0 if blocked/invuln).
    ``blocked`` is True if something blocked the damage (not just invulnerable).
    ``invulnerable`` is True if the target was invulnerable (damage completely ignored).
    ``killed`` is True if the target's health reached 0 or below.
    ``overkill`` is how much damage exceeded 0 health (positive when killed).
    """

    dealt: float = 0.0
    blocked: bool = False
    invulnerable: bool = False
    killed: bool = False
    overkill: float = 0.0


class DamageTarget(Protocol):
    """What the damage pipeline interacts with on the receiving side.

    Anything with a health value and invulnerability state implements this.
    """

    @property
    def health(self) -> float: ...

    @health.setter
    def health(self, value: float) -> None: ...

    @property
    def max_health(self) -> float: ...

    @property
    def invulnerable(self) -> bool: ...


class DamagePipeline:
    """Stateless pipeline: apply a DamageInstance to a DamageTarget.

    The pipeline handles:
      - Invulnerability check (damage completely ignored)
      - Damage application (subtract from target health)
      - Overkill tracking (how much damage exceeded 0 HP)
    """

    def apply(
        self,
        instance: DamageInstance,
        target: DamageTarget,
    ) -> DamageResult:
        """Apply one damage instance to one target.

        Does NOT publish events — the caller is responsible for publishing
        after receiving the result (keeps the pipeline testable and pure).
        """
        if instance.value <= 0.0:
            return DamageResult()

        if target.invulnerable:
            return DamageResult(invulnerable=True)

        new_health = target.health - instance.value
        killed = new_health <= 0.0
        overkill = -new_health if killed else 0.0
        dealt = instance.value - overkill

        if killed:
            target.health = 0.0
        else:
            target.health = new_health

        return DamageResult(
            dealt=dealt,
            killed=killed,
            overkill=overkill,
        )

    def apply_multi(
        self,
        instances: list[DamageInstance],
        target: DamageTarget,
    ) -> list[DamageResult]:
        """Apply multiple damage instances sequentially.

        After the first kill, remaining instances are skipped (dead targets
        cannot take further damage).
        """
        results: list[DamageResult] = []
        for instance in instances:
            if target.health <= 0.0:
                break
            results.append(self.apply(instance, target))
        return results
