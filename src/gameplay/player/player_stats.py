"""Player stats: every gameplay number lives in data files (RULES.md section 7).

``PlayerStats`` is the typed, validated view over a data/player document
(data/player/stats.yaml, schema data/schemas/player.schema.yaml). Current
values are PROVISIONAL greybox tuning, not balance decisions; tuning happens
in YAML, never in code. Class-specific stats arrive later through the same
data-driven pipeline (L3: Warrior first, architecture class-agnostic).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class PlayerStatsError(ValueError):
    """Raised when a player stats document is missing or malformed."""


@dataclass(frozen=True)
class PlayerStats:
    """Immutable, data-driven player configuration (class-agnostic base)."""

    # Movement (world pixels / second, px / second^2).
    move_speed: float
    acceleration: float
    friction: float
    # Dodge / roll (world pixels, seconds).
    roll_distance: float
    roll_duration: float
    dodge_invulnerability: float
    # Resources.
    max_health: float
    max_mana: float
    attack_speed: float
    # Collision boxes (world pixels, offsets relative to body center).
    body_width: float
    body_height: float
    hitbox_width: float
    hitbox_height: float
    hitbox_offset_x: float
    hitbox_offset_y: float
    hurtbox_width: float
    hurtbox_height: float
    hurtbox_offset_x: float
    hurtbox_offset_y: float

    @property
    def roll_speed(self) -> float:
        """Constant roll velocity derived from distance / duration."""
        return self.roll_distance / self.roll_duration

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> PlayerStats:
        """Build stats from a data/player document; raise on any problem."""
        source = str(document.get("id", "<unknown>"))
        stats = document.get("stats")
        if not isinstance(stats, dict):
            raise PlayerStatsError(
                f"player document '{source}' has no 'stats' mapping"
            )
        problems: list[str] = []

        def read(group: str, key: str) -> float:
            node = stats.get(group)
            if not isinstance(node, dict):
                problems.append(f"missing group '{group}'")
                return 1.0
            value = node.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                problems.append(f"'{group}.{key}' must be a number")
                return 1.0
            if value <= 0:
                problems.append(f"'{group}.{key}' must be positive")
            return float(value)

        def read_box(group: str, key: str, default: float) -> float:
            node = stats.get(group)
            if node is None:
                return default
            if not isinstance(node, dict):
                problems.append(f"'{group}' must be a mapping")
                return default
            value = node.get(key, 0.0 if "offset" in key else default)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                problems.append(f"'{group}.{key}' must be a number")
                return default
            if "offset" not in key and value <= 0:
                problems.append(f"'{group}.{key}' must be positive")
            return float(value)

        body_width = read("body", "width")
        body_height = read("body", "height")
        kwargs = {
            "move_speed": read("movement", "move_speed"),
            "acceleration": read("movement", "acceleration"),
            "friction": read("movement", "friction"),
            "roll_distance": read("dodge", "roll_distance"),
            "roll_duration": read("dodge", "roll_duration"),
            "dodge_invulnerability": read("dodge", "invulnerability"),
            "max_health": read("resources", "max_health"),
            "max_mana": read("resources", "max_mana"),
            "attack_speed": read("resources", "attack_speed"),
            "body_width": body_width,
            "body_height": body_height,
            # Hitbox/hurtbox default to the body box when not specified.
            "hitbox_width": read_box("hitbox", "width", body_width),
            "hitbox_height": read_box("hitbox", "height", body_height),
            "hitbox_offset_x": read_box("hitbox", "offset_x", 0.0),
            "hitbox_offset_y": read_box("hitbox", "offset_y", 0.0),
            "hurtbox_width": read_box("hurtbox", "width", body_width),
            "hurtbox_height": read_box("hurtbox", "height", body_height),
            "hurtbox_offset_x": read_box("hurtbox", "offset_x", 0.0),
            "hurtbox_offset_y": read_box("hurtbox", "offset_y", 0.0),
        }
        if problems:
            raise PlayerStatsError(
                f"invalid player stats in '{source}': "
                + "; ".join(sorted(set(problems)))
            )
        return cls(**kwargs)
