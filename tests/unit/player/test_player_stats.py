"""Tests for gameplay.player.player_stats: data-driven config (Phase 3)."""

from __future__ import annotations

import pytest

from core.data_loader import load_category
from gameplay.player.player_stats import PlayerStats, PlayerStatsError

VALID_DOCUMENT = {
    "id": "test_player",
    "stats": {
        "movement": {"move_speed": 120.0, "acceleration": 1000.0, "friction": 1300.0},
        "dodge": {
            "roll_distance": 76.0,
            "roll_duration": 0.34,
            "invulnerability": 0.26,
        },
        "resources": {"max_health": 100.0, "max_mana": 50.0, "attack_speed": 1.0},
        "body": {"width": 14.0, "height": 12.0},
        "hitbox": {"width": 22.0, "height": 16.0},
        "hurtbox": {"width": 12.0, "height": 12.0},
    },
}


def test_from_document_reads_every_value() -> None:
    stats = PlayerStats.from_document(VALID_DOCUMENT)
    assert stats.move_speed == 120.0
    assert stats.acceleration == 1000.0
    assert stats.friction == 1300.0
    assert stats.roll_distance == 76.0
    assert stats.roll_duration == 0.34
    assert stats.dodge_invulnerability == 0.26
    assert stats.max_health == 100.0
    assert stats.max_mana == 50.0
    assert stats.attack_speed == 1.0
    assert stats.body_width == 14.0
    assert stats.hitbox_width == 22.0
    assert stats.hurtbox_height == 12.0


def test_roll_speed_is_derived() -> None:
    stats = PlayerStats.from_document(VALID_DOCUMENT)
    assert stats.roll_speed == pytest.approx(76.0 / 0.34)


def test_boxes_default_to_body_size_and_zero_offsets() -> None:
    keep = ("movement", "dodge", "resources", "body")
    document = {
        "id": "minimal",
        "stats": {k: v for k, v in VALID_DOCUMENT["stats"].items() if k in keep},
    }
    stats = PlayerStats.from_document(document)
    assert stats.hitbox_width == stats.body_width
    assert stats.hurtbox_height == stats.body_height
    assert stats.hitbox_offset_x == 0.0
    assert stats.hurtbox_offset_y == 0.0


def test_missing_stats_mapping_raises() -> None:
    with pytest.raises(PlayerStatsError, match="stats"):
        PlayerStats.from_document({"id": "broken"})


def test_missing_required_key_raises_with_name() -> None:
    document = {
        "id": "broken",
        "stats": {**VALID_DOCUMENT["stats"], "movement": {"move_speed": 1.0}},
    }
    with pytest.raises(PlayerStatsError, match="movement"):
        PlayerStats.from_document(document)


def test_non_numeric_value_raises() -> None:
    document = {
        "id": "broken",
        "stats": {
            **VALID_DOCUMENT["stats"],
            "body": {"width": "wide", "height": 12.0},
        },
    }
    with pytest.raises(PlayerStatsError, match="body.width"):
        PlayerStats.from_document(document)


def test_non_positive_value_raises() -> None:
    document = {
        "id": "broken",
        "stats": {
            **VALID_DOCUMENT["stats"],
            "resources": {"max_health": -5.0, "max_mana": 50.0, "attack_speed": 1.0},
        },
    }
    with pytest.raises(PlayerStatsError, match="max_health"):
        PlayerStats.from_document(document)


def test_shipped_player_data_loads_from_data_dir() -> None:
    """The real data/player/stats.yaml must parse into valid stats."""
    documents = load_category("player")
    ids = [doc.document.get("id") for doc in documents]
    assert "player_base" in ids
    document = next(
        doc.document for doc in documents if doc.document.get("id") == "player_base"
    )
    stats = PlayerStats.from_document(document)
    assert stats.move_speed > 0.0
    assert stats.dodge_invulnerability <= stats.roll_duration
    assert stats.roll_speed > stats.move_speed  # a roll must outpace running
