"""Reward system: data-driven temporary run buffs with 3-choice selection.

Phase 8 greybox: simple stat-boosting rewards.
Architecture designed for future expansion (tags, blessings, passives, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RewardTag(Enum):
    """Future-proofing: tag category for synergy engine (Phase 8+)."""

    OFFENSE = "offense"
    DEFENSE = "defense"
    MOBILITY = "mobility"
    UTILITY = "utility"


@dataclass(frozen=True)
class RewardDefinition:
    """One reward option: what it does and how it's presented."""

    id: str
    name: str
    description: str
    tags: frozenset[str] = frozenset()

    # Stat modifications (applied to player on selection).
    damage_bonus: float = 0.0
    health_bonus: float = 0.0
    speed_bonus: float = 0.0
    attack_speed_bonus: float = 0.0
    dodge_charge_bonus: int = 0


# Greybox reward pool — data-driven; extend via YAML in future phases.
_REWARD_POOL: list[RewardDefinition] = [
    RewardDefinition(
        "dmg_up",
        "Barbed Edge",
        "Attack +20%",
        tags=frozenset({"offense"}),
        damage_bonus=0.20,
    ),
    RewardDefinition(
        "dmg_up2",
        "Sharpened Steel",
        "Attack +15%",
        tags=frozenset({"offense"}),
        damage_bonus=0.15,
    ),
    RewardDefinition(
        "hp_up",
        "Vitality Charm",
        "Max HP +30",
        tags=frozenset({"defense"}),
        health_bonus=30.0,
    ),
    RewardDefinition(
        "hp_up2",
        "Fortified Heart",
        "Max HP +20",
        tags=frozenset({"defense"}),
        health_bonus=20.0,
    ),
    RewardDefinition(
        "spd_up",
        "Wind Step",
        "Move speed +15%",
        tags=frozenset({"mobility"}),
        speed_bonus=0.15,
    ),
    RewardDefinition(
        "spd_up2",
        "Swift Boots",
        "Move speed +10%",
        tags=frozenset({"mobility"}),
        speed_bonus=0.10,
    ),
    RewardDefinition(
        "aspd_up",
        "Quick Hands",
        "Attack speed +20%",
        tags=frozenset({"offense"}),
        attack_speed_bonus=0.20,
    ),
    RewardDefinition(
        "dodge_up",
        "Evasive Maneuver",
        "+1 dodge charge",
        tags=frozenset({"mobility"}),
        dodge_charge_bonus=1,
    ),
]


def get_random_rewards(count: int = 3) -> list[RewardDefinition]:
    """Pick N random rewards from the pool (seeded externally)."""
    import random

    return random.sample(_REWARD_POOL, min(count, len(_REWARD_POOL)))


def apply_reward(reward: RewardDefinition, player: Any) -> None:
    """Apply a reward's effects to the player in-place."""
    if reward.damage_bonus:
        # Multiply the base attack damage.
        old = player.attack_executor.data.damage
        player.attack_executor = player.attack_executor.__class__(
            _patch_attack_data(
                player.attack_executor.data, damage=old * (1.0 + reward.damage_bonus)
            )
        )
    if reward.health_bonus:
        player.stats = _patch_stats(
            player.stats, max_health=player.stats.max_health + reward.health_bonus
        )
        player.health += reward.health_bonus
    if reward.speed_bonus:
        player.stats = _patch_stats(
            player.stats,
            move_speed=player.stats.move_speed * (1.0 + reward.speed_bonus),
        )
    if reward.attack_speed_bonus:
        player.stats = _patch_stats(
            player.stats,
            attack_speed=player.stats.attack_speed * (1.0 + reward.attack_speed_bonus),
        )
    if reward.dodge_charge_bonus:
        player.stats = _patch_stats(
            player.stats,
            dodge_max_charges=player.stats.dodge_max_charges
            + reward.dodge_charge_bonus,
        )
        player.dodge_charges = player.dodge_charges.__class__(
            max_charges=player.stats.dodge_max_charges,
            cooldown=player.stats.dodge_cooldown,
        )


def _patch_attack_data(data, **kwargs) -> Any:
    """Create a new AttackData with overridden fields."""
    from dataclasses import replace

    return replace(data, **kwargs)


def _patch_stats(stats, **kwargs) -> Any:
    """Create a new PlayerStats with overridden fields."""
    from dataclasses import replace

    return replace(stats, **kwargs)
