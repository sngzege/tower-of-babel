"""Tests for core.dependency_container (infrastructure only)."""

from __future__ import annotations

import pytest

from core.dependency_container import DependencyContainer


def test_register_and_resolve_instance() -> None:
    container = DependencyContainer()
    container.register_instance("answer", 42)
    assert container.resolve("answer") == 42


def test_singleton_factory_called_once() -> None:
    container = DependencyContainer()
    calls: list[int] = []
    container.register_factory("obj", lambda _c: calls.append(1) or object())
    first = container.resolve("obj")
    second = container.resolve("obj")
    assert first is second
    assert len(calls) == 1


def test_transient_factory_called_each_time() -> None:
    container = DependencyContainer()
    container.register_factory("obj", lambda _c: object(), singleton=False)
    assert container.resolve("obj") is not container.resolve("obj")


def test_unknown_dependency_raises() -> None:
    container = DependencyContainer()
    with pytest.raises(KeyError):
        container.resolve("missing")


def test_duplicate_registration_raises() -> None:
    container = DependencyContainer()
    container.register_instance("x", 1)
    with pytest.raises(ValueError):
        container.register_instance("x", 2)
