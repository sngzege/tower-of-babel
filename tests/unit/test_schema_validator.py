"""Tests for tools/data_validation/schema_validator.py (infrastructure)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from schema_validator import SchemaError, apply_defaults, load_schema, validate_document


@pytest.fixture()
def schema() -> dict[str, Any]:
    return {
        "fields": {
            "id": {"type": "str", "required": True, "pattern": "^[a-z][a-z0-9_]*$"},
            "power": {"type": "int", "min": 0, "max": 10, "default": 0},
            "tags": {"type": "list", "item": "str", "default": []},
            "kind": {"type": "str", "enum": ["a", "b"]},
        }
    }


def test_valid_document_passes(schema: dict[str, Any]) -> None:
    assert validate_document({"id": "valid_id", "kind": "a"}, schema) == []


def test_missing_required(schema: dict[str, Any]) -> None:
    assert validate_document({}, schema) == ["id: missing required field"]


def test_pattern_enforced(schema: dict[str, Any]) -> None:
    problems = validate_document({"id": "Bad Id"}, schema)
    assert any("pattern" in p for p in problems)


def test_min_max_enforced(schema: dict[str, Any]) -> None:
    problems = validate_document({"id": "ok", "power": 99}, schema)
    assert any("max" in p for p in problems)


def test_enum_enforced(schema: dict[str, Any]) -> None:
    problems = validate_document({"id": "ok", "kind": "z"}, schema)
    assert any("enum" in p for p in problems)


def test_list_item_type_enforced(schema: dict[str, Any]) -> None:
    problems = validate_document({"id": "ok", "tags": ["fine", 3]}, schema)
    assert any("tags[1]" in p for p in problems)


def test_bool_is_not_int(schema: dict[str, Any]) -> None:
    problems = validate_document({"id": "ok", "power": True}, schema)
    assert any("power" in p for p in problems)


def test_defaults_applied(schema: dict[str, Any]) -> None:
    result = apply_defaults({"id": "ok"}, schema)
    assert result["power"] == 0
    assert result["tags"] == []


def test_load_schema_requires_fields(tmp_path: Path) -> None:
    path = tmp_path / "bad.schema.yaml"
    path.write_text("schema: nope\n", encoding="utf-8")
    with pytest.raises(SchemaError):
        load_schema(path)


def test_shipped_schemas_validate_their_own_examples() -> None:
    """Every schema in data/schemas/ must have a valid embedded example."""
    schemas_dir = Path(__file__).resolve().parents[2] / "data" / "schemas"
    schema_files = sorted(schemas_dir.glob("*.schema.yaml"))
    assert schema_files, "no schema files found"
    for schema_file in schema_files:
        schema = load_schema(schema_file)
        example = schema.get("example")
        assert example is not None, f"{schema_file.name}: missing example"
        problems = validate_document(example, schema, location=schema_file.name)
        assert problems == [], f"{schema_file.name}: {problems}"
