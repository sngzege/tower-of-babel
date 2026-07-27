"""Tests for utils.config_loader (infrastructure only)."""

from __future__ import annotations

from pathlib import Path

import pytest

from utils.config_loader import ConfigError, ConfigLoader, deep_merge, load_yaml_file


def test_load_yaml_file_returns_mapping(tmp_path: Path) -> None:
    path = tmp_path / "sample.yaml"
    path.write_text("window:\n  width: 1280\n", encoding="utf-8")
    assert load_yaml_file(path) == {"window": {"width": 1280}}


def test_load_yaml_file_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_yaml_file(tmp_path / "missing.yaml")


def test_load_yaml_file_rejects_non_mapping(tmp_path: Path) -> None:
    path = tmp_path / "list.yaml"
    path.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_yaml_file(path)


def test_load_yaml_file_comment_only_is_empty_mapping(tmp_path: Path) -> None:
    path = tmp_path / "empty.yaml"
    path.write_text("# nothing here\n", encoding="utf-8")
    assert load_yaml_file(path) == {}


def test_deep_merge_nested() -> None:
    base = {"a": {"x": 1, "y": 2}, "b": 1}
    override = {"a": {"y": 3}}
    assert deep_merge(base, override) == {"a": {"x": 1, "y": 3}, "b": 1}


def test_config_loader_caches_and_reloads(tmp_path: Path) -> None:
    (tmp_path / "display.yaml").write_text("vsync: true\n", encoding="utf-8")
    loader = ConfigLoader(config_dir=tmp_path)
    assert loader.load("display") == {"vsync": True}
    (tmp_path / "display.yaml").write_text("vsync: false\n", encoding="utf-8")
    assert loader.load("display") == {"vsync": True}  # cached
    loader.reload("display")
    assert loader.load("display") == {"vsync": False}
