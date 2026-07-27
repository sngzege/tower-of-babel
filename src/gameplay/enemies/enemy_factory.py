"""Enemy factory: builds Enemy entities from registry documents.

Flow:
  ContentRegistry -> enemy document (dict)
       -> EnemyConfig.from_document(document)
       -> Enemy(config, x, y)
       -> optionally wrap with SimpleAI

The factory decouples enemy creation from battle/room setup code.
Greybox only for now — supports one enemy type (greybox_dummy).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.content_registry import ContentRegistry
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
