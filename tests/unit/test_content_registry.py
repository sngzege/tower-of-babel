"""Tests for core.data_loader and core.content_registry (infrastructure)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from core.content_registry import ContentRegistry, RegistryError
from core.data_loader import DataDocument, DataError, load_category


def _doc(content_id: str, **extra: Any) -> DataDocument:
    return DataDocument(
        category="things",
        document={"id": content_id, **extra},
        source=Path("fake.yaml"),
    )


def test_register_and_get() -> None:
    registry = ContentRegistry()
    registry.register(_doc("alpha", tags=["x"]))
    assert registry.get("things", "alpha")["id"] == "alpha"


def test_duplicate_id_raises() -> None:
    registry = ContentRegistry()
    registry.register(_doc("alpha"))
    with pytest.raises(RegistryError):
        registry.register(_doc("alpha"))


def test_missing_id_raises() -> None:
    registry = ContentRegistry()
    entry = DataDocument(
        category="things", document={"name": "no id"}, source=Path("f.yaml")
    )
    with pytest.raises(RegistryError):
        registry.register(entry)


def test_query_by_tag() -> None:
    registry = ContentRegistry()
    registry.register(_doc("alpha", tags=["fire"]))
    registry.register(_doc("beta", tags=["ice"]))
    registry.register(_doc("gamma"))
    results = registry.query_by_tag("things", "fire")
    assert [d["id"] for d in results] == ["alpha"]


def test_freeze_blocks_registration() -> None:
    registry = ContentRegistry()
    registry.register(_doc("alpha"))
    registry.freeze()
    with pytest.raises(RegistryError):
        registry.register(_doc("beta"))


def test_unknown_get_raises() -> None:
    registry = ContentRegistry()
    with pytest.raises(RegistryError):
        registry.get("things", "missing")


def test_load_category_reads_yaml_files(tmp_path: Path) -> None:
    category_dir = tmp_path / "things" / "sub"
    category_dir.mkdir(parents=True)
    (category_dir / "one.yaml").write_text("id: one\ntags: [x]\n", encoding="utf-8")
    documents = load_category("things", data_dir=tmp_path)
    assert len(documents) == 1
    assert documents[0].document["id"] == "one"
    assert documents[0].category == "things"


def test_load_category_skips_comment_only_placeholders(tmp_path: Path) -> None:
    category_dir = tmp_path / "things"
    category_dir.mkdir()
    (category_dir / "placeholder.yaml").write_text(
        "# placeholder only\n", encoding="utf-8"
    )
    (category_dir / "real.yaml").write_text("id: real\n", encoding="utf-8")
    documents = load_category("things", data_dir=tmp_path)
    assert [d.document["id"] for d in documents] == ["real"]


def test_load_category_still_rejects_invalid_yaml(tmp_path: Path) -> None:
    category_dir = tmp_path / "things"
    category_dir.mkdir()
    (category_dir / "bad.yaml").write_text("id: [unclosed\n", encoding="utf-8")
    with pytest.raises(DataError):
        load_category("things", data_dir=tmp_path)


def test_load_category_rejects_non_mapping_content(tmp_path: Path) -> None:
    category_dir = tmp_path / "things"
    category_dir.mkdir()
    (category_dir / "list.yaml").write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(DataError):
        load_category("things", data_dir=tmp_path)
