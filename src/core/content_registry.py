"""Content registry: how systems discover content without hardcoding it.

Content flow: data files -> data_loader -> registry -> game systems
(see docs/architecture/DATA_FLOW.md). The registry stores plain documents and
answers queries by id and tag. It performs only structural checks; semantic
validation belongs to the schema validator (tools/data_validation).
Infrastructure only - no game content is defined here.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from core.data_loader import DataDocument
from utils.logger import get_logger

_logger = get_logger(__name__)


class RegistryError(Exception):
    """Raised for duplicate, invalid, or missing content."""


class ContentRegistry:
    """Id-indexed store for any number of content categories."""

    def __init__(self) -> None:
        self._items: dict[str, dict[str, DataDocument]] = {}
        self._validators: list[Callable[[str, dict[str, Any], Path], None]] = []
        self._frozen = False

    def add_validator(
        self, validator: Callable[[str, dict[str, Any], Path], None]
    ) -> None:
        """Add a check run on each document: (category, document, source)."""
        self._validators.append(validator)

    def register(self, entry: DataDocument) -> None:
        if self._frozen:
            raise RegistryError("Registry is frozen (run started); no registration")
        document = entry.document
        content_id = document.get("id")
        if not isinstance(content_id, str) or not content_id:
            raise RegistryError(f"Content without a string 'id' in {entry.source}")
        category_items = self._items.setdefault(entry.category, {})
        if content_id in category_items:
            raise RegistryError(
                f"Duplicate id '{content_id}' in category '{entry.category}': "
                f"{entry.source} conflicts with {category_items[content_id].source}"
            )
        for validator in self._validators:
            validator(entry.category, document, entry.source)
        category_items[content_id] = entry

    def register_all(self, entries: Iterable[DataDocument]) -> int:
        count = 0
        for entry in entries:
            self.register(entry)
            count += 1
        return count

    def freeze(self) -> None:
        """Lock the registry before a run starts (no mutation during gameplay)."""
        self._frozen = True

    def get(self, category: str, content_id: str) -> dict[str, Any]:
        try:
            return self._items[category][content_id].document
        except KeyError as exc:
            raise RegistryError(f"Unknown {category} id: '{content_id}'") from exc

    def has(self, category: str, content_id: str) -> bool:
        return content_id in self._items.get(category, {})

    def all(self, category: str) -> list[dict[str, Any]]:
        return [entry.document for entry in self._items.get(category, {}).values()]

    def query_by_tag(self, category: str, tag: str) -> list[dict[str, Any]]:
        """All documents of a category whose 'tags' list contains ``tag``."""
        return [
            document
            for document in self.all(category)
            if tag in (document.get("tags") or [])
        ]

    def count(self, category: str) -> int:
        return len(self._items.get(category, {}))
