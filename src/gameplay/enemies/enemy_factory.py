"""Enemy factory: builds Enemy entities from registry documents.

Flow:
  ContentRegistry -> enemy document (dict)
       -> EnemyConfig.from_document(document)
       -> Enemy(config, x, y)
       -> optionally wrap with SimpleAI or BossAI

The factory decouples enemy creation from battle/room setup code.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.content_registry import ContentRegistry
from gameplay.combat.attack import AttackData
from gameplay.enemies.enemy import Enemy, EnemyConfig
from gameplay.enemies.enemy_ai import SimpleAI

# Registry of per-id post-build hooks (extend for Phase 5+ enemy types).
_ENEMY_HOOKS: dict[str, Callable[[Enemy], None]] = {}


def register_enemy_hook(enemy_id: str, hook: Callable[[Enemy], None]) -> None:
    """Register a post-build hook for a specific enemy type.

    Hooks run after the Enemy is created but before it's returned,
    allowing specialized setup (custom AI, equipment, etc.).
    """
    _ENEMY_HOOKS[enemy_id] = hook


def build_enemy(
    registry: ContentRegistry,
    enemy_id: str,
    x: float = 0.0,
    y: float = 0.0,
) -> tuple[Enemy, SimpleAI]:
    """Build an Enemy + SimpleAI from a registered data document.

    Args:
        registry: ContentRegistry with 'enemies' category loaded.
        enemy_id: Document id (e.g. 'greybox_dummy').
        x, y: Spawn world position.

    Returns:
        (Enemy, SimpleAI) — both already linked.

    Raises:
        RegistryError if enemy_id not found.
    """
    document: dict[str, Any] = registry.get("enemies", enemy_id)
    config = EnemyConfig.from_document(document)
    enemy = Enemy(config=config, x=x, y=y)

    # Run any registered per-type hooks.
    hook = _ENEMY_HOOKS.get(enemy_id)
    if hook is not None:
        hook(enemy)

    ai = SimpleAI(enemy)
    return enemy, ai


def build_boss(
    registry: ContentRegistry,
    boss_id: str,
    x: float = 0.0,
    y: float = 0.0,
    primary_attack: AttackData | None = None,
    aoe_attack: AttackData | None = None,
) -> tuple[Enemy, Any]:
    """Build an Enemy + BossAI from a registered data document."""
    document: dict[str, Any] = registry.get("enemies", boss_id)
    config = EnemyConfig.from_document(document)
    enemy = Enemy(config=config, x=x, y=y)

    # Build attack data for boss (use provided or defaults from config).
    p_attack = primary_attack or AttackData(
        id=f"{boss_id}_primary",
        windup=config.attack_windup,
        active=config.attack_active,
        recovery=config.attack_recovery,
        cooldown=config.attack_cooldown,
        damage=config.attack_damage,
        damage_types=config.attack_damage_types,
        hitbox_spread=config.attack_hitbox_spread,
        hitbox_reach=config.attack_hitbox_reach,
    )

    # Lazy import to break circular dependency.
    from gameplay.bosses.boss_ai import BossAI  # noqa: C0415

    boss_ai = BossAI(enemy, primary_attack_data=p_attack, aoe_attack_data=aoe_attack)

    # Apply Phase 2 speed boost from document if available.
    phase2 = document.get("phase2", {})
    if "speed" in phase2:
        boss_ai._p2_speed = float(phase2["speed"])

    return enemy, boss_ai
