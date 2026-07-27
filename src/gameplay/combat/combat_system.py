"""Combat system: orchestrates hit resolution each frame.

Ties together:
  - Damage pipeline (damage application)
  - Attack executor lifecycle (windup/active/recovery/cooldown)
  - Invulnerability service (per-entity invulnerability checks)
  - Status effect framework (applying and ticking effects)

Each frame, the scene collects active hitboxes from all entities and
vulnerable hurtboxes from all entities, then calls CombatSystem.resolve_hits()
to detect overlaps and apply damage. The system publishes events so audio,
UI, and other systems can react without importing combat internals.

Integration with Player:
  Player gains an ``attack_executor`` and an ``invulnerability_service``.
  The PlaytestScene (or future combat component) calls combat_system.update()
  every frame with the active lists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.events import EventBus
from gameplay.combat.damage import DamageInstance, DamagePipeline, DamageResult
from gameplay.combat.invulnerability import InvulnerabilityService
from gameplay.combat.status_effects import StatusEffectData, StatusEffectManager
from physics.collision import AABB

EVENT_ENTITY_DAMAGED = "entity_damaged"
EVENT_ENTITY_KILLED = "entity_killed"
EVENT_ATTACK_STARTED = "attack_started"
EVENT_ATTACK_HIT = "attack_hit"
EVENT_INVULN_CHANGED = "invulnerability_changed"
EVENT_STATUS_APPLIED = "status_applied"
EVENT_STATUS_EXPIRED = "status_expired"


@dataclass
class CombatEntity:
    """Data about one combat-participating entity for the resolver.

    The scene or owning system assembles these each frame from the
    components of players, enemies, etc.
    """

    id: str
    body_x: float
    body_y: float
    hurtbox_aabb: AABB
    vulnerable: bool
    damage_target: Any  # DamageTarget protocol implementor
    status_manager: StatusEffectManager | None = None
    invuln_service: InvulnerabilityService | None = None


@dataclass
class ResolvedHit:
    """One hit that connected: source attack + target entity + result."""

    source_id: str
    target_id: str
    instance: DamageInstance
    result: DamageResult


class CombatSystem:
    """Orchestrates hit resolution and attack lifecycle each frame.

    Call order each frame:
      1. update_attacks(dt)  — advance all active attack executors
      2. resolve_hits(...)   — check hitbox/hurtbox overlaps, apply damage
      3. resolve_status(...) — apply status effects from damage instances
    """

    def __init__(self, events: EventBus | None = None) -> None:
        self.pipeline = DamagePipeline()
        self._events = events

    # -- Hit resolution --

    def resolve_hits(
        self,
        hitboxes: list[tuple[str, AABB, DamageInstance]],
        entities: list[CombatEntity],
    ) -> list[ResolvedHit]:
        """Check all hitboxes against all vulnerable hurtboxes.

        ``hitboxes`` is a list of (source_id, aabb, damage_instance) from
        active attacks this frame.

        ``entities`` is the list of targetable entities with their hurtboxes.

        Returns all hits that connected (target was vulnerable and not
        invulnerable). The caller is responsible for:
          - Publishing EVENT_ENTITY_DAMAGED / EVENT_ENTITY_KILLED
          - Updating target health (already applied by the pipeline)
        """
        hits: list[ResolvedHit] = []

        for source_id, hb_aabb, damage in hitboxes:
            for entity in entities:
                if not entity.vulnerable:
                    continue
                if not hb_aabb.intersects(entity.hurtbox_aabb):
                    continue

                # Check entity-level invulnerability.
                invuln = (
                    entity.invuln_service.invulnerable
                    if entity.invuln_service
                    else False
                )
                if invuln:
                    # Still record a hit for attack-on-invulnerable effects
                    # (parry, shield break, etc.) but with zero damage dealt.
                    hits.append(
                        ResolvedHit(
                            source_id=source_id,
                            target_id=entity.id,
                            instance=damage,
                            result=DamageResult(invulnerable=True),
                        )
                    )
                    if self._events:
                        self._events.publish(
                            EVENT_ATTACK_HIT,
                            source=source_id,
                            target=entity.id,
                            result="invulnerable",
                            damage=damage,
                        )
                    continue

                # Apply damage.
                result = self.pipeline.apply(damage, entity.damage_target)

                hits.append(
                    ResolvedHit(
                        source_id=source_id,
                        target_id=entity.id,
                        instance=damage,
                        result=result,
                    )
                )

                if self._events:
                    self._events.publish(
                        EVENT_ENTITY_DAMAGED,
                        source=source_id,
                        target=entity.id,
                        dealt=result.dealt,
                        killed=result.killed,
                        types=list(damage.types),
                        knockback=damage.knockback,
                    )
                    self._events.publish(
                        EVENT_ATTACK_HIT,
                        source=source_id,
                        target=entity.id,
                        result="hit",
                        damage=damage,
                    )
                    if result.killed:
                        self._events.publish(
                            EVENT_ENTITY_KILLED,
                            source=source_id,
                            target=entity.id,
                            overkill=result.overkill,
                        )

        return hits

    # -- Status effects --

    def apply_status(
        self,
        status_tags: frozenset[str],
        manager: StatusEffectManager,
        registry: dict[str, StatusEffectData],
    ) -> list[str]:
        """Apply status effects from a damage instance's status_tags.

        Looks up each tag in the registry; if a matching StatusEffectData
        is found, applies it to the manager. Returns effect ids that
        were newly applied or refreshed.
        """
        applied: list[str] = []
        for tag in status_tags:
            effect_data = registry.get(tag)
            if effect_data is not None:
                changed = manager.apply(effect_data)
                if changed and self._events:
                    self._events.publish(
                        EVENT_STATUS_APPLIED,
                        effect_id=effect_data.id,
                        duration=effect_data.duration,
                    )
                    applied.append(effect_data.id)
        return applied

    def update_status(
        self,
        managers: list[tuple[str, StatusEffectManager]],
        dt: float,
    ) -> dict[str, list[str]]:
        """Tick all status effect managers. Returns {entity_id: [expired_ids]}."""
        expired: dict[str, list[str]] = {}
        for entity_id, manager in managers:
            expired_ids = manager.update(dt)
            if expired_ids:
                expired[entity_id] = expired_ids
                if self._events:
                    for eid in expired_ids:
                        self._events.publish(
                            EVENT_STATUS_EXPIRED,
                            entity_id=entity_id,
                            effect_id=eid,
                        )
        return expired

    # -- Invulnerability --

    def update_invulnerability(
        self,
        services: list[InvulnerabilityService],
        dt: float,
    ) -> None:
        """Tick all invulnerability services."""
        for service in services:
            service.update(dt)
