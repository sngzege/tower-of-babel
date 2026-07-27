"""YAML configuration loading with defaults merging.

Loads technical configuration from config/*.yaml (see PROJECT_STRUCTURE.md).
Configuration is technical only - it must never contain game content
(RULES.md section 23).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from utils.file_utils import find_project_root


class ConfigError(Exception):
    """Raised when a configuration file cannot be loaded."""


def load_yaml_file(path: Path) -> dict[str, Any]:
    """Load a YAML file that must contain a mapping at its root."""
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"Config root must be a mapping: {path}")
    return data


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Return ``base`` updated recursively with ``override`` (override wins)."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class ConfigLoader:
    """Load and cache configs by short name ('display' -> config/display.yaml)."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or find_project_root() / "config"
        self._cache: dict[str, dict[str, Any]] = {}

    def load(self, name: str, defaults: dict[str, Any] | None = None) -> dict[str, Any]:
        if name in self._cache:
            return self._cache[name]
        data = load_yaml_file(self.config_dir / f"{name}.yaml")
        if defaults:
            data = deep_merge(defaults, data)
        self._cache[name] = data
        return data

    def reload(self, name: str | None = None) -> None:
        if name is None:
            self._cache.clear()
        else:
            self._cache.pop(name, None)
