"""Tests for Phase 10 build integration: abilities, passives, weapon upgrades, class loadout.

Verifies:
  - Ability activation and cooldown
  - Passive modifier application
  - Passive + boon interaction
  - Weapon upgrades apply and reset
  - Class loadout loading
  - Build reset on new run
  - Combined weapon + passive + boon integration
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from core.content_registry import ContentRegistry
from core.data_loader import load_category
from gameplay.builds.ability import AbilityData, AbilityExecutor
from gameplay.builds.boon import BoonData, apply_boon_to_build
from gameplay.builds.build_state import BuildState
from gameplay.builds.passive import PassiveData
from gameplay.builds.weapon import WeaponData
from gameplay.combat.attack import AttackData

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture(scope="module")
def registry() -> ContentRegistry:
    reg = ContentRegistry()
    for category in ("weapons", "boons", "abilities", "passives", "classes", "combat", "player"):
        for entry in load_category(category, data_dir=_DATA_DIR):
            reg.register(entry)
    return reg


# -- Ability System --


def test_ability_executor_activation() -> None:
    data = AbilityData(id="test", name="Test", cooldown=3.0)
    exec_ = AbilityExecutor(data)
    assert exec_.can_activate()
    assert exec_.activate()
    assert not exec_.can_activate()  # on cooldown
    exec_.update(3.0)
    assert exec_.can_activate()


def test_ability_cooldown_timing() -> None:
    data = AbilityData(id="test", name="Test", cooldown=1.5)
    exec_ = AbilityExecutor(data)
    exec_.activate()
    exec_.update(0.5)
    assert not exec_.can_activate()
    exec_.update(1.0)
    assert exec_.can_activate()


def test_ability_loads_from_data(registry: ContentRegistry) -> None:
    for aid in ("warrior_charge", "warrior_shield_bash", "warrior_whirlwind", "warrior_war_cry"):
        doc = registry.get("abilities", aid)
        data = AbilityData.from_document(doc)
        assert data.id == aid
        assert data.cooldown >= 0
        assert len(data.effects) >= 1
        assert data.ability_type in ("instant", "toggle")


def test_ability_cannot_activate_twice() -> None:
    data = AbilityData(id="test", name="Test", cooldown=1.0)
    exec_ = AbilityExecutor(data)
    assert exec_.activate()
    assert not exec_.activate()  # already activated
    exec_.update(1.0)
    assert exec_.activate()


# -- Passive System --


def test_passive_loads_from_data(registry: ContentRegistry) -> None:
    for pid in ("hardy", "fury"):
        doc = registry.get("passives", pid)
        data = PassiveData.from_document(doc)
        assert data.id == pid
        assert len(data.modifiers) >= 1


def test_passive_applies_modifier_to_build() -> None:
    build = BuildState()
    doc = {"id": "test_hardy", "name": "Test Hardy", "modifiers": [
        {"stat": "max_health", "value": 25.0, "is_percent": False}
    ]}
    passive = PassiveData.from_document(doc)
    for mod in passive.modifiers:
        tag_str = next(iter(mod.tags)) if mod.tags else ""
        build.apply_passive_modifier(mod.stat, mod.value, mod.is_percent, tag_str)
    assert build.max_health_bonus == 25.0


def test_passive_damage_modifier() -> None:
    build = BuildState()
    doc = {"id": "test_fury", "name": "Test Fury", "modifiers": [
        {"stat": "damage", "value": 0.15, "is_percent": True}
    ]}
    passive = PassiveData.from_document(doc)
    for mod in passive.modifiers:
        tag_str = next(iter(mod.tags)) if mod.tags else ""
        build.apply_passive_modifier(mod.stat, mod.value, mod.is_percent, tag_str)
    assert build.damage_mult == pytest.approx(1.15)


def test_passive_resets_with_build() -> None:
    build = BuildState()
    build.apply_passive_modifier("max_health", 25.0, False)
    assert build.max_health_bonus == 25.0
    build.reset()
    assert build.max_health_bonus == 0.0


# -- Weapon Upgrades --


def test_weapon_upgrade_applies() -> None:
    build = BuildState()
    build.add_weapon_upgrade("damage", 0.15)
    assert build.get_weapon_upgrade("damage") == 0.15


def test_weapon_upgrade_stacks() -> None:
    build = BuildState()
    build.add_weapon_upgrade("damage", 0.10)
    build.add_weapon_upgrade("damage", 0.20)
    assert build.get_weapon_upgrade("damage") == pytest.approx(0.30)


def test_weapon_upgrade_resets_with_build() -> None:
    build = BuildState()
    build.add_weapon_upgrade("damage", 0.50)
    build.reset()
    assert build.get_weapon_upgrade("damage") == 0.0


def test_weapon_upgrade_modifies_attack_data() -> None:
    """Weapon upgrades should affect attack data through re-application."""
    weapon = WeaponData.from_document({
        "id": "test_sword", "name": "Sword", "tags": ["melee", "sweep"],
        "attack_ref": "sword_attack", "damage_mult": 1.0,
    })
    base = AttackData(id="test", damage=20.0, cooldown=0.5,
                      hitbox_reach=38.0, hitbox_spread=20.0)
    applied = weapon.apply_to_attack(base)

    # Apply a weapon upgrade.
    build = BuildState()
    build.add_weapon_upgrade("damage", 0.20)

    # Simulate what _reapply_weapon does.
    dmg_bonus = build.get_weapon_upgrade("damage", 0.0)
    if dmg_bonus:
        applied = replace(applied, damage=applied.damage * (1.0 + dmg_bonus))

    assert applied.damage == pytest.approx(24.0)  # 20 * 1.20


# -- Class Loadout --


def test_warrior_class_loads(registry: ContentRegistry) -> None:
    doc = registry.get("classes", "warrior")
    assert doc.get("starting_weapon") == "warrior_sword"
    assert len(doc.get("starting_abilities", {})) == 4
    assert len(doc.get("starting_passives", [])) >= 1


def test_class_weapon_exists_in_registry(registry: ContentRegistry) -> None:
    """Warrior's starting weapon should load successfully."""
    doc = registry.get("classes", "warrior")
    weapon_id = doc.get("starting_weapon", "")
    assert weapon_id
    weapon_doc = registry.get("weapons", weapon_id)
    assert weapon_doc is not None


def test_class_abilities_exist(registry: ContentRegistry) -> None:
    """All abilities referenced by the warrior class must exist."""
    doc = registry.get("classes", "warrior")
    abilities = doc.get("starting_abilities", {})
    for slot, ability_id in abilities.items():
        ability_doc = registry.get("abilities", ability_id)
        assert ability_doc is not None, f"Ability '{ability_id}' for slot '{slot}' not found"


# -- Combined Integration --


def test_passive_and_boon_both_affect_build() -> None:
    build = BuildState()

    # Add a passive.
    build.apply_passive_modifier("damage", 0.15, True)
    assert build.damage_mult == pytest.approx(1.15)

    # Add a boon.
    boon = BoonData(
        id="test_dmg", name="Test", description="", tags=frozenset(),
        effects=({"stat": "damage", "value": 0.20, "is_percent": True},),
    )
    apply_boon_to_build(boon, build)
    assert build.damage_mult == pytest.approx(1.15 * 1.20)


def test_weapon_with_passive_and_boon_damage() -> None:
    """Weapon base damage modified by passive + boon should stack correctly."""
    build = BuildState()

    # Passive: +15% damage.
    build.apply_passive_modifier("damage", 0.15, True)
    # Boon: +20% damage.
    boon = BoonData("b1", "B", "", frozenset(),
                    ({"stat": "damage", "value": 0.20, "is_percent": True},))
    apply_boon_to_build(boon, build)

    # Weapon: sword with 20 base damage.
    base = AttackData(id="test", damage=20.0, cooldown=0.5,
                      hitbox_reach=38.0, hitbox_spread=20.0)
    weapon = WeaponData("test_sword", "Sword", attack_ref="test")
    applied = weapon.apply_to_attack(base)

    # Apply build damage multiplier.
    final_damage = applied.damage * build.damage_mult
    assert final_damage == pytest.approx(20.0 * 1.15 * 1.20)  # = 27.6


def test_weapon_upgrade_plus_boon() -> None:
    """Weapon upgrade + boon both affect final damage."""
    build = BuildState()

    # Boon: +20% damage.
    boon = BoonData("b1", "B", "", frozenset(),
                    ({"stat": "damage", "value": 0.20, "is_percent": True},))
    apply_boon_to_build(boon, build)

    # Weapon upgrade: +15% damage.
    build.add_weapon_upgrade("damage", 0.15)

    # Weapon: sword with 20 base.
    weapon = WeaponData("test_sword", "Sword", attack_ref="test")
    base = AttackData(id="test", damage=20.0, cooldown=0.5, hitbox_reach=38.0, hitbox_spread=20.0)
    applied = weapon.apply_to_attack(base)

    # Apply upgrade.
    dmg_bonus = build.get_weapon_upgrade("damage", 0.0)
    if dmg_bonus:
        applied = replace(applied, damage=applied.damage * (1.0 + dmg_bonus))

    # Apply boon damage multiplier.
    final_damage = applied.damage * build.damage_mult
    assert final_damage == pytest.approx(20.0 * 1.15 * 1.20)


def test_full_build_reset_on_new_run() -> None:
    """All build components must reset on new run."""
    build = BuildState()

    # Add everything.
    build.weapon_id = "warrior_sword"
    build.ability_ids.append("warrior_charge")
    build.passive_ids.append("hardy")
    apply_boon_to_build(
        BoonData("b1", "B", "", frozenset(),
                 ({"stat": "damage", "value": 0.20, "is_percent": True},)),
        build
    )
    build.add_weapon_upgrade("damage", 0.15)
    build.apply_passive_modifier("max_health", 25.0, False)

    # Verify state before reset.
    assert build.damage_mult > 1.0
    assert build.max_health_bonus > 0
    assert len(build.boon_ids) == 1

    # Reset.
    build.reset()
    assert build.weapon_id == "unarmed"
    assert build.ability_ids == []
    assert build.passive_ids == []
    assert build.boon_ids == []
    assert build.weapon_upgrades == {}
    assert build.damage_mult == 1.0
    assert build.max_health_bonus == 0.0


def test_ability_acquisition_via_boon() -> None:
    """Acquiring an ability via a boon should add to build state."""
    build = BuildState()
    boon = BoonData(
        "gain_charge", "Momentum", "", frozenset({"mobility", "ability"}),
        ({"type": "grant_ability", "ability_id": "warrior_charge"},),
    )
    apply_boon_to_build(boon, build)
    assert "warrior_charge" in build.ability_ids


def test_passive_acquisition_via_boon() -> None:
    """Acquiring a passive via a boon should add to build state."""
    build = BuildState()
    boon = BoonData(
        "gain_hardy", "Enduring", "", frozenset({"defense", "passive"}),
        ({"type": "grant_passive", "passive_id": "hardy"},),
    )
    apply_boon_to_build(boon, build)
    assert "hardy" in build.passive_ids
