"""Minimal dependency container (service registry).

Systems receive collaborators explicitly instead of reaching for globals
(RULES.md section 12: avoid global state, explicit dependencies).
Infrastructure only.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class DependencyContainer:
    """Registers singletons and factories by name."""

    def __init__(self) -> None:
        self._providers: dict[str, Callable[[DependencyContainer], Any]] = {}
        self._singletons: dict[str, Any] = {}

    def register_instance(self, name: str, instance: Any) -> None:
        self._ensure_free(name)
        self._singletons[name] = instance

    def register_factory(
        self,
        name: str,
        factory: Callable[[DependencyContainer], Any],
        *,
        singleton: bool = True,
    ) -> None:
        self._ensure_free(name)
        if singleton:

            def cached(container: DependencyContainer) -> Any:
                if name not in self._singletons:
                    self._singletons[name] = factory(container)
                return self._singletons[name]

            self._providers[name] = cached
        else:
            self._providers[name] = factory

    def resolve(self, name: str) -> Any:
        if name in self._singletons:
            return self._singletons[name]
        provider = self._providers.get(name)
        if provider is None:
            raise KeyError(f"No dependency registered under '{name}'")
        return provider(self)

    def has(self, name: str) -> bool:
        return name in self._singletons or name in self._providers

    def clear(self) -> None:
        self._providers.clear()
        self._singletons.clear()

    def _ensure_free(self, name: str) -> None:
        if self.has(name):
            raise ValueError(f"Dependency '{name}' is already registered")
