"""Tests for Phase 9 build system: BuildState, weapons, boons, modifiers.

Verifies:
  - BuildState starts empty and resets correctly
  - Weapons load from data files and modify attack data
  - Boons load from data and modify BuildState modifiers
  - Tag-specific modifiers work correctly
  - Global stat modifiers work correctly
  - Death resets build state
  - Weapon changes attack behavior
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.content_registry import ContentRegistry
from core.data_loader import load_category
from gameplay.builds.boon import BoonData, apply_boon_to_build
from gameplay.builds.build_state import BuildState
from gameplay.builds.weapon import WeaponData

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture(scope="module")
def registry() -> ContentRegistry:
    reg = ContentRegistry()
    for category in ("weapons", "boons", "combat", "player", "passives", "abilities"):
        for entry in load_category(category, data_dir=_DATA_DIR):
            reg.register(entry)
    return reg


# -- BuildState --


def test_build_state_starts_empty() -> None:
    build = BuildState()
    assert build.weapon_id == "unarmed"
    assert build.ability_ids == []
    assert build.passive_ids == []
    assert build.boon_ids == []
    assert build.damage_mult == 1.0
    assert build.move_speed_mult == 1.0
    assert build.attack_speed_mult == 1.0
    assert build.max_health_bonus == 0.0
    assert build.dodge_charge_bonus == 0
    assert build.crit_chance == 0.0


def test_build_state_reset_clears_modifiers() -> None:
    build = BuildState()
    # Apply some modifiers.
    build._damage_mult = 2.0
    build._tag_mods[("damage", "melee")] = 0.25
    build.reset()
    assert build.damage_mult == 1.0
    assert build._tag_mods == {}


def test_build_state_total_damage() -> None:
    build = BuildState()
    # No modifiers → no change.
    assert build.total_damage_for(20.0, frozenset({"physical"})) == 20.0

    # Global damage boost.
    build._damage_mult = 1.5
    assert build.total_damage_for(20.0, frozenset({"physical"})) == 30.0

    # Tag-specific boost.
    build._tag_mods[("damage", "melee")] = 0.25
    result = build.total_damage_for(20.0, frozenset({"physical", "melee"}))
    assert result == pytest.approx(37.5)  # 20 * 1.5 * 1.25

    # Tags that don't match → no extra boost.
    result2 = build.total_damage_for(20.0, frozenset({"physical", "ranged"}))
    assert result2 == 30.0  # only global, no tag boost


def test_build_state_speed_modifiers() -> None:
    build = BuildState()
    assert build.total_speed_for(100.0) == 100.0
    build._move_speed_mult = 1.2
    assert build.total_speed_for(100.0) == 120.0


# -- Weapons --


def test_weapon_data_loads(registry: ContentRegistry) -> None:
    for wid in ("warrior_sword", "warrior_spear", "warrior_axe"):
        doc = registry.get("weapons", wid)
        weapon = WeaponData.from_document(doc)
        assert weapon.id == wid
        assert weapon.name
        assert weapon.attack_ref
        assert weapon.tags


def test_weapon_tags_differ() -> None:
    """Sword and spear should have different tags for synergy testing."""
    sword = WeaponData.from_document({
        "id": "test_sword", "name": "Sword", "tags": ["melee", "sweep"],
        "attack_ref": "sword_attack",
    })
    spear = WeaponData.from_document({
        "id": "test_spear", "name": "Spear", "tags": ["melee", "thrust", "piercing"],
        "attack_ref": "spear_attack",
    })
    assert "sweep" in sword.tags
    assert "piercing" in spear.tags
    assert "sweep" not in spear.tags


def test_weapon_modifies_attack_data(registry: ContentRegistry) -> None:
    """Spear should have longer reach than sword."""
    sword_doc = registry.get("weapons", "warrior_sword")
    spear_doc = registry.get("weapons", "warrior_spear")

    sword = WeaponData.from_document(sword_doc)
    spear = WeaponData.from_document(spear_doc)

    assert spear.reach_mult > sword.reach_mult  # spear has longer reach
    assert spear.damage_mult >= sword.damage_mult  # spear more damage


# -- Boons --


def test_boon_loads_from_data(registry: ContentRegistry) -> None:
    for bid in ("boon_damage_up", "boon_hp_up", "boon_speed_up", "boon_melee_damage", "boon_piercing_damage"):
        doc = registry.get("boons", bid)
        boon = BoonData.from_document(doc)
        assert boon.id == bid
        assert boon.name
        assert len(boon.effects) >= 1


def test_boon_global_damage_applies_to_build() -> None:
    build = BuildState()
    boon = BoonData(
        id="test_dmg", name="Test Dmg", description="+20% damage",
        tags=frozenset(),
        effects=({"stat": "damage", "value": 0.20, "is_percent": True},),
    )
    apply_boon_to_build(boon, build)
    assert build.damage_mult == pytest.approx(1.20)
    assert "test_dmg" in build.boon_ids


def test_boon_tag_damage_applies_to_build() -> None:
    build = BuildState()
    boon = BoonData(
        id="test_melee", name="Melee Boost", description="", tags=frozenset(),
        effects=({"stat": "damage", "tag": "melee", "value": 0.25, "is_percent": True},),
    )
    apply_boon_to_build(boon, build)
    assert build.tag_mult("damage", "melee") == 0.25
    assert build.tag_mult("damage", "ranged") == 0.0


def test_boon_health_applies() -> None:
    build = BuildState()
    boon = BoonData(
        id="test_hp", name="HP Up", description="", tags=frozenset(),
        effects=({"stat": "max_health", "value": 30.0, "is_percent": False},),
    )
    apply_boon_to_build(boon, build)
    assert build.max_health_bonus == 30.0


def test_multiple_boons_stack() -> None:
    build = BuildState()
    dmg = BoonData(
        id="d1", name="Dmg", description="", tags=frozenset(),
        effects=({"stat": "damage", "value": 0.20, "is_percent": True},),
    )
    hp = BoonData(
        id="h1", name="HP", description="", tags=frozenset(),
        effects=({"stat": "max_health", "value": 30.0, "is_percent": False},),
    )
    apply_boon_to_build(dmg, build)
    apply_boon_to_build(hp, build)
    assert build.damage_mult == pytest.approx(1.20)
    assert build.max_health_bonus == 30.0


def test_boon_with_tag_synergy() -> None:
    """Piercing boon only affects attacks with the piercing tag."""
    build = BuildState()
    boon = BoonData(
        id="pierce_boost", name="Impaler", description="", tags=frozenset(),
        effects=({"stat": "damage", "tag": "piercing", "value": 0.35, "is_percent": True},),
    )
    apply_boon_to_build(boon, build)

    # Damage with piercing tag gets the bonus.
    dmg_pierce = build.total_damage_for(20.0, frozenset({"physical", "piercing"}))
    assert dmg_pierce == pytest.approx(27.0)  # 20 * 1.35

    # Damage without piercing tag doesn't.
    dmg_normal = build.total_damage_for(20.0, frozenset({"physical", "melee"}))
    assert dmg_normal == 20.0


def test_build_reset_clears_boons() -> None:
    build = BuildState()
    boon = BoonData(
        id="d1", name="Dmg", description="", tags=frozenset(),
        effects=({"stat": "damage", "value": 0.20, "is_percent": True},),
    )
    apply_boon_to_build(boon, build)
    assert build.damage_mult > 1.0
    build.reset()
    assert build.damage_mult == 1.0
    assert build.boon_ids == []


# -- Combo build paths --


def test_sword_melee_build_path() -> None:
    """Sword + melee damage boon → damage boost with correct tags."""
    build = BuildState()
    build.weapon_id = "warrior_sword"

    boon = BoonData(
        id="melee_dmg", name="Close Quarters", description="", tags=frozenset(),
        effects=({"stat": "damage", "tag": "melee", "value": 0.25, "is_percent": True},),
    )
    apply_boon_to_build(boon, build)

    # Sword has melee + sweep tags.
    sword_tags = frozenset({"physical", "melee", "sweep"})
    result = build.total_damage_for(20.0, sword_tags)
    assert result == pytest.approx(25.0)  # 20 * 1.25

    # Ranged tag (not in sword) should not get the bonus.
    result2 = build.total_damage_for(20.0, frozenset({"physical", "ranged"}))
    assert result2 == 20.0


def test_spear_piercing_build_path() -> None:
    """Spear + piercing boon → damage bonus only for piercing attacks."""
    build = BuildState()
    build.weapon_id = "warrior_spear"

    dmg = BoonData(
        id="dmg", name="Dmg", description="", tags=frozenset(),
        effects=({"stat": "damage", "value": 0.15, "is_percent": True},),
    )
    pierce = BoonData(
        id="pierce", name="Impaler", description="", tags=frozenset(),
        effects=({"stat": "damage", "tag": "piercing", "value": 0.35, "is_percent": True},),
    )
    apply_boon_to_build(dmg, build)
    apply_boon_to_build(pierce, build)

    # Spear has piercing tag → gets global + piercing bonus.
    tags = frozenset({"physical", "melee", "thrust", "piercing"})
    result = build.total_damage_for(22.0, tags)
    assert result == pytest.approx(22.0 * 1.15 * 1.35)

    # Non-piercing tags only get global.
    result2 = build.total_damage_for(22.0, frozenset({"physical", "melee", "sweep"}))
    assert result2 == pytest.approx(22.0 * 1.15)
