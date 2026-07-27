"""Status effect framework: tag-based effect slots with tick/expire lifecycle.

Framework-only — no specific effects are defined here (content requires
human approval per RULES.md §3). The framework provides:

  - StatusEffectData: immutable effect template (id, duration, tags, modifiers)
  - StatusEffectInstance: runtime instance with tick timer
  - StatusEffectManager: applies, ticks, expires effects on one entity

Usage:
    manager = StatusEffectManager()
    manager.apply(burn_data)
    manager.update(dt)  # returns expired effect ids
    if manager.has_tag("fire"):
        # apply fire damage this frame
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StatusEffectData:
    """Immutable effect template from data files.

    ``id`` — unique effect identifier (e.g. "burn", "slow", "stun").
    ``name`` — human-readable name.
    ``duration`` — how long the effect lasts (0.0 = instant/one-shot).
    ``tick_interval`` — time between ticks (0.0 = no periodic ticks).
    ``tags`` — keyword tags for grouping, synergy, and immunity checks.
    ``modifiers`` — stat/behavior changes, keyed by modifier name.
    ``max_stacks`` — maximum concurrent stacks (1 = unique-only).
    """

    id: str
    name: str = ""
    duration: float = 0.0
    tick_interval: float = 0.0
    tags: frozenset[str] = frozenset()
    modifiers: dict[str, float] = field(default_factory=dict)
    max_stacks: int = 1


@dataclass
class StatusEffectInstance:
    """One active effect on an entity."""

    data: StatusEffectData
    remaining: float  # seconds until expiry
    tick_timer: float = 0.0  # seconds since last tick
    stacks: int = 1


class StatusEffectManager:
    """Manages status effects for one entity.

    Each effect is grouped by its ``id``; applying the same effect
    increments stacks (up to ``max_stacks``) and refreshes the duration.
    """

    def __init__(self) -> None:
        self._effects: dict[str, StatusEffectInstance] = {}

    # -- Query --

    @property
    def active(self) -> list[StatusEffectInstance]:
        """All currently active effects (expired ones already removed)."""
        return list(self._effects.values())

    def has(self, effect_id: str) -> bool:
        """True if the given effect is currently active."""
        return effect_id in self._effects

    def has_tag(self, tag: str) -> bool:
        """True if any active effect carries the given tag."""
        return any(tag in inst.data.tags for inst in self._effects.values())

    def get(self, effect_id: str) -> StatusEffectInstance | None:
        """Get the active instance of an effect by id."""
        return self._effects.get(effect_id)

    def get_modifier(self, key: str, default: float = 0.0) -> float:
        """Aggregate modifier value across all active effects.

        Modifiers from different effects are summed (e.g. two 0.8 speed
        multipliers stack to 0.8 + 0.8 = 1.6 additive, then applied as a
        multiplier via the consuming system).
        """
        total = 0.0
        for inst in self._effects.values():
            total += inst.data.modifiers.get(key, 0.0)
        return total

    # -- Mutation --

    def apply(self, effect_data: StatusEffectData) -> bool:
        """Apply an effect. Returns True if anything changed.

        If the effect is already active:
          - Stacks are incremented (up to max_stacks).
          - Duration is refreshed to the data's full duration.
        """
        if effect_data.duration <= 0.0:
            return False  # instant effects with no duration do nothing here

        existing = self._effects.get(effect_data.id)
        if existing is not None:
            # Refresh and stack.
            existing.remaining = effect_data.duration
            if existing.stacks < effect_data.max_stacks:
                existing.stacks += 1
            return True

        self._effects[effect_data.id] = StatusEffectInstance(
            data=effect_data,
            remaining=effect_data.duration,
        )
        return True

    def remove(self, effect_id: str) -> bool:
        """Immediately remove an effect. Returns True if it was active."""
        if effect_id in self._effects:
            del self._effects[effect_id]
            return True
        return False

    def update(self, dt: float) -> list[str]:
        """Advance timers, tick, expire effects.

        Returns a list of effect ids that expired this frame (callers can
        publish events or apply tick effects).
        """
        expired: list[str] = []
        for effect_id, inst in list(self._effects.items()):
            inst.remaining -= dt
            if inst.remaining <= 0.0:
                expired.append(effect_id)
                del self._effects[effect_id]
                continue

            if inst.data.tick_interval > 0.0:
                inst.tick_timer += dt
                # Tick every tick_interval (excess carries over for precise timing).
                # We don't accumulate multiple ticks in one frame to avoid
                # burst damage — the caller applies one tick per frame.
                if inst.tick_timer >= inst.data.tick_interval:
                    inst.tick_timer -= inst.data.tick_interval

        return expired

    def clear(self) -> None:
        """Remove all effects immediately."""
        self._effects.clear()
