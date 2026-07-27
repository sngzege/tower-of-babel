"""Tests for the save infrastructure: schema, manager, migrations."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.constants import SAVE_VERSION
from save.migrations import MigrationError, MigrationRegistry
from save.save_manager import SaveError, SaveManager
from save.save_schema import new_save_template, validate_save_structure


def test_template_is_valid() -> None:
    assert validate_save_structure(new_save_template()) == []


def test_structure_validation_reports_missing_keys() -> None:
    problems = validate_save_structure({"meta": {}})
    assert any("persistent" in p for p in problems)
    assert any("run_state" in p for p in problems)


def test_roundtrip(tmp_path: Path) -> None:
    manager = SaveManager(path=tmp_path / "save.yaml")
    save = new_save_template()
    save["persistent"] = {"village": {"tier": 1}}
    manager.write(save)
    loaded = manager.read()
    assert loaded["persistent"] == {"village": {"tier": 1}}
    assert loaded["meta"]["save_version"] == SAVE_VERSION
    assert loaded["run_state"] is None


def test_write_rejects_invalid(tmp_path: Path) -> None:
    manager = SaveManager(path=tmp_path / "save.yaml")
    with pytest.raises(SaveError):
        manager.write({"meta": {}})


def test_read_missing_raises(tmp_path: Path) -> None:
    manager = SaveManager(path=tmp_path / "save.yaml")
    with pytest.raises(SaveError):
        manager.read()


def test_read_or_new_returns_template_when_absent(tmp_path: Path) -> None:
    manager = SaveManager(path=tmp_path / "save.yaml")
    assert validate_save_structure(manager.read_or_new()) == []


def test_newer_version_is_refused_not_silenced(tmp_path: Path) -> None:
    manager = SaveManager(path=tmp_path / "save.yaml")
    save = new_save_template()
    save["meta"]["save_version"] = SAVE_VERSION + 5
    manager.write(save)
    with pytest.raises(SaveError):
        manager.read()


def test_migration_chain_applied() -> None:
    registry = MigrationRegistry()
    for version in range(1, SAVE_VERSION):
        registry.register(version, lambda save: save)
    save = new_save_template()
    save["meta"]["save_version"] = 1
    migrated = registry.migrate(save)
    assert migrated["meta"]["save_version"] == SAVE_VERSION


def test_missing_migration_raises() -> None:
    if SAVE_VERSION < 2:
        pytest.skip("no migrations needed at version 1")
    registry = MigrationRegistry()
    save = new_save_template()
    save["meta"]["save_version"] = 1
    with pytest.raises(MigrationError):
        registry.migrate(save)
