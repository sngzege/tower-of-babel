"""Save file reading and writing.

Writes are atomic (utils.file_utils.write_text_atomic); payloads are versioned
(core.constants.SAVE_VERSION) and migrated on load (save.migrations).
Infrastructure only - which fields systems store inside 'persistent' and
'run_state' is defined by those systems when they are built.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from core.constants import SAVES_DIR
from save.migrations import MigrationError, MigrationRegistry
from save.save_schema import new_save_template, validate_save_structure
from utils.file_utils import ensure_dir, write_text_atomic
from utils.logger import get_logger

_logger = get_logger(__name__)


class SaveManager:
    """Manages one save-slot file (default: saves/save_1.yaml)."""

    def __init__(
        self,
        path: Path | None = None,
        migrations: MigrationRegistry | None = None,
    ) -> None:
        self.path = path or (SAVES_DIR / "save_1.yaml")
        self._migrations = migrations or MigrationRegistry()

    def exists(self) -> bool:
        return self.path.is_file()

    def write(self, save: dict[str, Any]) -> None:
        problems = validate_save_structure(save)
        if problems:
            raise SaveError(f"Refusing to write invalid save: {problems}")
        save["meta"]["updated_at"] = datetime.now(UTC).isoformat()
        ensure_dir(self.path.parent)
        write_text_atomic(
            self.path, yaml.safe_dump(save, sort_keys=False, allow_unicode=True)
        )
        _logger.info("Save written: %s", self.path)

    def read(self) -> dict[str, Any]:
        if not self.exists():
            raise SaveError(f"No save file at {self.path}")
        try:
            data = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise SaveError(f"Save file is not valid YAML: {self.path}: {exc}") from exc
        problems = validate_save_structure(data)
        if problems:
            raise SaveError(f"Save file failed structural validation: {problems}")
        try:
            return self._migrations.migrate(data)
        except MigrationError as exc:
            raise SaveError(str(exc)) from exc

    def read_or_new(self) -> dict[str, Any]:
        """Load the save if present, otherwise return a fresh template."""
        return self.read() if self.exists() else new_save_template()

    def delete(self) -> None:
        if self.exists():
            self.path.unlink()


class SaveError(Exception):
    """Raised when a save cannot be written or loaded."""
