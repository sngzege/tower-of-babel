"""Save migration registry.

Migrations upgrade an older save payload step by step to the current
SAVE_VERSION. RULES.md section 18: future migrations must be supported and old
saves must never be silently invalidated. No migrations exist yet (version 1);
this is the registry they will plug into.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.constants import SAVE_VERSION

Migration = Callable[[dict[str, Any]], dict[str, Any]]


class MigrationError(Exception):
    """Raised when a save cannot be migrated to the current version."""


class MigrationRegistry:
    """Ordered chain of migrations: register(N, fn) upgrades version N -> N+1."""

    def __init__(self) -> None:
        self._migrations: dict[int, Migration] = {}

    def register(self, from_version: int, migration: Migration) -> None:
        if from_version in self._migrations:
            raise ValueError(
                f"Migration from version {from_version} already registered"
            )
        self._migrations[from_version] = migration

    def migrate(self, save: dict[str, Any]) -> dict[str, Any]:
        version = save.get("meta", {}).get("save_version")
        if not isinstance(version, int):
            raise MigrationError("Save has no integer meta.save_version")
        if version > SAVE_VERSION:
            raise MigrationError(
                f"Save version {version} is newer than supported {SAVE_VERSION}; "
                "refusing to load instead of silently invalidating it"
            )
        while version < SAVE_VERSION:
            migration = self._migrations.get(version)
            if migration is None:
                raise MigrationError(f"No migration registered from version {version}")
            save = migration(save)
            version += 1
            save.setdefault("meta", {})["save_version"] = version
        return save
