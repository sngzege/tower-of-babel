"""Minimal schema interpreter for the project's data files.

Schema files live in data/schemas/<name>.schema.yaml and describe what a valid
content document of that category looks like (docs/architecture/DATA_FLOW.md).
Deliberately small and dependency-light (pyyaml only). Used by the offline CLI
(tools/data_validation/validate_data.py) and available for development-time
registry validation.

Schema format (PROVISIONAL):

    schema: ability
    version: 1
    fields:
      id:    {type: str, required: true, pattern: '^[a-z][a-z0-9_]*$'}
      power: {type: int, min: 0, max: 10, default: 0}
      tags:  {type: list, item: str, default: []}
      kind:  {type: str, enum: [active, passive]}
      meta:  {type: dict, keys: {icon: {type: str}}}

Supported rules: type (str/int/float/bool/list/dict), required, default,
pattern (str), enum, min/max (numbers), min_length/max_length (str/list),
item (schema for list elements), keys (schemas for dict members).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_TYPE_CHECKS = {
    "str": lambda v: isinstance(v, str),
    "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "float": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "bool": lambda v: isinstance(v, bool),
    "list": lambda v: isinstance(v, list),
    "dict": lambda v: isinstance(v, dict),
}


class SchemaError(Exception):
    """Raised when a schema file itself is invalid."""


def load_schema(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("fields"), dict):
        raise SchemaError(f"Schema file must define a 'fields' mapping: {path}")
    return data


def validate_document(
    document: Any, schema: dict[str, Any], *, location: str = ""
) -> list[str]:
    """Validate one document against a schema. Returns a list of problems."""
    if not isinstance(document, dict):
        return [f"{location or '<document>'}: root is not a mapping"]
    problems: list[str] = []
    for name, rules in schema.get("fields", {}).items():
        rules = _normalize_rules(rules)
        value = document.get(name, rules.get("default"))
        path = f"{location}.{name}" if location else name
        if value is None:
            if rules.get("required"):
                problems.append(f"{path}: missing required field")
            continue
        problems.extend(_check_value(value, rules, path))
    return problems


def apply_defaults(document: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with schema defaults filled in for absent fields."""
    result = dict(document)
    for name, rules in schema.get("fields", {}).items():
        if name not in result and isinstance(rules, dict) and "default" in rules:
            result[name] = rules["default"]
    return result


def _normalize_rules(rules: Any) -> dict[str, Any]:
    """Allow shorthand: a plain string means {type: <string>}; None means {}."""
    if rules is None:
        return {}
    if isinstance(rules, str):
        return {"type": rules}
    return rules


def _check_value(value: Any, rules: dict[str, Any], path: str) -> list[str]:
    rules = _normalize_rules(rules)
    problems: list[str] = []
    type_name = rules.get("type")
    if type_name:
        check = _TYPE_CHECKS.get(type_name)
        if check is None:
            raise SchemaError(f"Unknown type '{type_name}' at {path}")
        if not check(value):
            problems.append(f"{path}: expected {type_name}, got {_type_name(value)}")
            return problems  # further checks would be meaningless
    if "enum" in rules and value not in rules["enum"]:
        problems.append(f"{path}: '{value}' not in enum {rules['enum']}")
    if (
        isinstance(value, str)
        and "pattern" in rules
        and not re.fullmatch(rules["pattern"], value)
    ):
        problems.append(f"{path}: '{value}' does not match pattern {rules['pattern']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "min" in rules and value < rules["min"]:
            problems.append(f"{path}: {value} < min {rules['min']}")
        if "max" in rules and value > rules["max"]:
            problems.append(f"{path}: {value} > max {rules['max']}")
    if isinstance(value, (str, list)):
        if "min_length" in rules and len(value) < rules["min_length"]:
            problems.append(f"{path}: shorter than min_length {rules['min_length']}")
        if "max_length" in rules and len(value) > rules["max_length"]:
            problems.append(f"{path}: longer than max_length {rules['max_length']}")
    if isinstance(value, list) and "item" in rules:
        for index, element in enumerate(value):
            problems.extend(_check_value(element, rules["item"], f"{path}[{index}]"))
    if isinstance(value, dict) and "keys" in rules:
        for key, key_rules in rules["keys"].items():
            key_rules = _normalize_rules(key_rules)
            key_value = value.get(key, key_rules.get("default"))
            key_path = f"{path}.{key}"
            if key_value is None:
                if key_rules.get("required"):
                    problems.append(f"{key_path}: missing required field")
                continue
            problems.extend(_check_value(key_value, key_rules, key_path))
    return problems


def _type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    for name in ("int", "float", "str", "list", "dict"):
        if _TYPE_CHECKS[name](value):
            return name
    return type(value).__name__
