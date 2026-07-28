"""Playtest verification script.

Runs the game in headless mode and verifies critical systems.
This is an automated smoke test for the build integration.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.content_registry import ContentRegistry
from core.data_loader import load_category

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_content_loads() -> None:
    """Verify all content categories load without errors."""
    registry = ContentRegistry()
    categories = [
        "player", "classes", "combat", "weapons", "abilities",
        "passives", "boons", "enemies", "world",
    ]
    for cat in categories:
        try:
            registry.register_all(load_category(cat, data_dir=DATA_DIR))
        except Exception as exc:
            print(f"FAIL: Category '{cat}' failed to load: {exc}")
            raise

    # Verify Warrior class.
    warrior = registry.get("classes", "warrior")
    assert warrior["starting_weapon"] == "warrior_sword"
    abilities = warrior.get("starting_abilities", {})
    assert len(abilities) == 4, f"Expected 4 abilities, got {len(abilities)}"
    assert "skill_1" in abilities
    assert "aura" in abilities

    # Verify all abilities exist.
    for slot, aid in abilities.items():
        ability_doc = registry.get("abilities", aid)
        effects = ability_doc.get("effects", [])
        assert len(effects) >= 1, f"Ability '{aid}' has no effects"

    # Verify starting passives exist.
    for pid in warrior.get("starting_passives", []):
        assert registry.has("passives", pid), f"Passive '{pid}' not found"

    # Verify weapons load.
    for wid in ("warrior_sword", "warrior_spear", "warrior_axe"):
        doc = registry.get("weapons", wid)
        assert doc["attack_ref"]

    # Verify boons load (including new categories).
    for bid in (
        "boon_damage_up", "boon_weapon_damage", "boon_gain_charge",
        "boon_gain_hardy", "boon_melee_damage", "boon_piercing_damage",
    ):
        doc = registry.get("boons", bid)
        assert len(doc.get("effects", [])) >= 1, f"Boon '{bid}' has no effects"

    print(f"OK: All {len(categories)} categories loaded successfully")
    print(f"OK: Warrior class has {len(abilities)} abilities, {len(warrior.get('starting_passives', []))} passives")
    print(f"OK: All referenced IDs validated")


def test_build_state_integration() -> None:
    """Verify BuildState modifier pipeline end-to-end."""
    from gameplay.builds.build_state import BuildState
    from gameplay.builds.boon import BoonData, apply_boon_to_build
    from gameplay.builds.passive import PassiveData

    build = BuildState()

    # Apply a passive.
    build.apply_passive_modifier("damage", 0.15, True)
    assert build.damage_mult == 1.15, f"Expected 1.15, got {build.damage_mult}"

    # Apply a boon.
    boon = BoonData(
        id="test_dmg", name="Test", description="", tags=frozenset(),
        effects=({"stat": "damage", "value": 0.20, "is_percent": True},),
    )
    apply_boon_to_build(boon, build)
    expected = 1.15 * 1.20
    assert abs(build.damage_mult - expected) < 0.001, (
        f"Expected {expected}, got {build.damage_mult}"
    )

    # Apply a weapon upgrade.
    build.add_weapon_upgrade("damage", 0.15)
    assert build.get_weapon_upgrade("damage") == 0.15

    # Reset.
    build.reset()
    assert build.damage_mult == 1.0
    assert build.weapon_upgrades == {}
    assert build.boon_ids == []
    print("OK: BuildState modifier pipeline verified")


def test_ability_cooldown() -> None:
    """Verify ability cooldown lifecycle."""
    from gameplay.builds.ability import AbilityData, AbilityExecutor

    data = AbilityData(id="test", name="Test", cooldown=2.0)
    exec_ = AbilityExecutor(data)

    assert exec_.can_activate()
    assert exec_.ready_fraction == 1.0

    exec_.activate()
    assert not exec_.can_activate()
    assert exec_.state.just_activated  # flag for scene to read
    assert exec_.ready_fraction < 1.0

    exec_.state.just_activated = False  # scene consumed it

    exec_.update(1.0)
    assert not exec_.can_activate()
    assert exec_.ready_fraction == 0.5

    exec_.update(1.0)
    assert exec_.can_activate()
    assert exec_.ready_fraction == 1.0
    print("OK: Ability cooldown lifecycle verified")


def test_gameplay_run_headless() -> None:
    """Run the game in headless mode for a short duration."""
    import os
    import subprocess

    result = subprocess.run(
        [sys.executable, "scripts/run.py",
         "--headless", "--frames", "300", "--log-level", "WARNING"],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1],
        timeout=30,
    )
    assert result.returncode == 0, (
        f"Headless run failed with code {result.returncode}\n{result.stderr}"
    )
    print("OK: Headless 300-frame run completed")


if __name__ == "__main__":
    test_content_loads()
    test_build_state_integration()
    test_ability_cooldown()
    test_gameplay_run_headless()
    print("\n=== ALL PLAYTEST VERIFICATIONS PASSED ===")
