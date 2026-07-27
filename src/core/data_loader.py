"""Data file loading for the data-driven content layer.

Reads content YAML from data/ (RULES.md section 7: data-driven design) and
produces plain documents (dicts). Interpreting documents belongs to game
systems; semantic validation belongs to the schema validator
(tools/data_validation, see docs/architecture/DATA_FLOW.md).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any, NamedTuple

import yaml

from core.constants import CONTENT_FILE_SUFFIXES, DATA_DIR
from utils.logger import get_logger

_logger = get_logger(__name__)


class DataError(Exception):
    """Raised when a data file cannot be read or is structurally unusable."""


class DataDocument(NamedTuple):
    """One loaded content document plus its origin for error reporting."""

    category: str
    document: dict[str, Any]
    source: Path


def load_data_file(path: Path, category: str) -> DataDocument:
    """Load a single YAML content file; the root must be a mapping."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise DataError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise DataError(f"Data file root must be a mapping: {path}")
    return DataDocument(category=category, document=data, source=path)


def iter_data_files(data_dir: Path, category: str) -> Iterator[Path]:
    """Yield content files of one category (data/<category>/**), stable order."""
    category_dir = data_dir / category
    if not category_dir.is_dir():
        return
    for path in sorted(category_dir.rglob("*")):
        if path.is_file() and path.suffix in CONTENT_FILE_SUFFIXES:
            yield path


def _is_placeholder(path: Path) -> bool:
    """True when a YAML file parses to None (comment-only placeholder).

    Invalid YAML is NOT a placeholder - load_data_file will report it.
    """
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) is None
    except yaml.YAMLError:
        return False


def load_category(category: str, data_dir: Path | None = None) -> list[DataDocument]:
    """Load every content file in one category directory.

    Comment-only placeholder files are skipped, not errors - consistent with
    tools/data_validation (see DATA_FLOW.md §5).
    """
    root = data_dir or DATA_DIR
    documents: list[DataDocument] = []
    skipped = 0
    for path in iter_data_files(root, category):
        if _is_placeholder(path):
            skipped += 1
            continue
        documents.append(load_data_file(path, category))
    _logger.debug(
        "Loaded %d document(s) for category '%s' (%d placeholder(s) skipped)",
        len(documents),
        category,
        skipped,
    )
    return documents
