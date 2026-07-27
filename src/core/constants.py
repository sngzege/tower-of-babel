"""Project-wide structural constants.

Infrastructure only - paths and versioning, never gameplay values
(RULES.md section 8: no magic gameplay values).
"""

from __future__ import annotations

from pathlib import Path

from utils.file_utils import find_project_root

PROJECT_ROOT: Path = find_project_root()

CONFIG_DIR: Path = PROJECT_ROOT / "config"
DATA_DIR: Path = PROJECT_ROOT / "data"
DATA_SCHEMAS_DIR: Path = DATA_DIR / "schemas"
ASSETS_DIR: Path = PROJECT_ROOT / "assets"
SAVES_DIR: Path = PROJECT_ROOT / "saves"
LOGS_DIR: Path = PROJECT_ROOT / "logs"

# RULES.md section 18: save data must be versioned.
SAVE_VERSION: int = 1

CONTENT_FILE_SUFFIXES: tuple[str, ...] = (".yaml", ".yml")
