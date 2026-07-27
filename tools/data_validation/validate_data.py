"""Offline data validator CLI.

Walks data/, validates every content document against its category schema in
data/schemas/, checks embedded schema examples, and reports all problems.
Exit code 0 = all valid.

Usage:
    python tools/data_validation/validate_data.py [data_dir]

Category mapping (PROVISIONAL): the top-level folder under data/ maps to a
schema name via CATEGORY_SCHEMAS; SCHEMA_OVERRIDES handles second-level
folders that have their own schema (e.g. items/equipment, enemies/bosses).
Extend both mappings when new content categories are approved.
Empty (comment-only) placeholder files are skipped, not errors.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

# Allow running both as a module and as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from schema_validator import SchemaError, load_schema, validate_document  # noqa: E402

from core.constants import DATA_DIR, DATA_SCHEMAS_DIR  # noqa: E402
from core.data_loader import iter_data_files  # noqa: E402

CATEGORY_SCHEMAS: dict[str, str] = {
    "player": "player",
    "classes": "class",
    "abilities": "ability",
    "passives": "passive",
    "weapons": "weapon",
    "items": "item",
    "enemies": "enemy",
    "loot": "loot_table",
    "world": "stage",
    "npcs": "npc",
    "village": "building",
    "unlocks": "unlock",
    "progression": "progression",
}

# (category, second-level folder) -> schema name
SCHEMA_OVERRIDES: dict[tuple[str, str], str] = {
    ("items", "equipment"): "equipment",
    ("enemies", "bosses"): "boss",
    ("world", "rooms"): "room",
    ("world", "stages"): "stage",
    ("village", "upgrades"): "village_upgrade",
}


def _schema_name_for(category: str, path: Path, category_dir: Path) -> str:
    relative = path.relative_to(category_dir)
    if len(relative.parts) > 1:
        override = SCHEMA_OVERRIDES.get((category, relative.parts[0]))
        if override:
            return override
    return CATEGORY_SCHEMAS[category]


def validate_all(data_dir: Path, schemas_dir: Path) -> tuple[list[str], int]:
    """Validate everything. Returns (problems, skipped_placeholder_count)."""
    problems: list[str] = []
    skipped = 0
    if not schemas_dir.is_dir():
        return [f"schemas directory not found: {schemas_dir}"], skipped

    schema_cache: dict[str, dict] = {}

    def get_schema(name: str) -> dict | None:
        if name not in schema_cache:
            schema_path = schemas_dir / f"{name}.schema.yaml"
            if not schema_path.is_file():
                problems.append(f"missing schema: {schema_path.name}")
                schema_cache[name] = {}
                return None
            try:
                schema_cache[name] = load_schema(schema_path)
            except SchemaError as exc:
                problems.append(str(exc))
                schema_cache[name] = {}
                return None
        return schema_cache[name] or None

    for category in sorted(CATEGORY_SCHEMAS):
        category_dir = data_dir / category
        if not category_dir.is_dir():
            continue
        for path in iter_data_files(data_dir, category):
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            if raw is None:
                skipped += 1  # comment-only placeholder file
                continue
            schema_name = _schema_name_for(category, path, category_dir)
            schema = get_schema(schema_name)
            if schema is None:
                continue
            problems.extend(validate_document(raw, schema, location=str(path)))

    # Every schema's embedded example must validate against its own schema.
    for schema_path in sorted(schemas_dir.glob("*.schema.yaml")):
        try:
            schema = load_schema(schema_path)
        except SchemaError as exc:
            problems.append(str(exc))
            continue
        example = schema.get("example")
        if example is not None:
            problems.extend(
                validate_document(
                    example, schema, location=f"{schema_path.name}#example"
                )
            )
    return problems, skipped


def main(argv: list[str]) -> int:
    data_dir = Path(argv[1]) if len(argv) > 1 else DATA_DIR
    schemas_dir = (
        data_dir / "schemas" if (data_dir / "schemas").is_dir() else DATA_SCHEMAS_DIR
    )
    problems, skipped = validate_all(data_dir, schemas_dir)
    if problems:
        print(f"Data validation FAILED with {len(problems)} problem(s):")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"Data validation OK ({skipped} placeholder file(s) skipped).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
