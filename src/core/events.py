"""Synchronous event bus for loose coupling between systems.

Systems publish named events; interested systems subscribe. Neither side
imports the other (see docs/architecture/ARCHITECTURE.md - dependency rules).
Infrastructure only - no gameplay event names are defined here; event
vocabulary gets defined by the systems that own it as they are built.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from utils.logger import get_logger

_logger = get_logger(__name__)


@dataclass(frozen=True)
class Event:
    """An immutable event message. ``payload`` is a plain dict of attributes."""

    name: str
    payload: dict[str, Any] = field(default_factory=dict)


class EventBus:
    """Minimal synchronous pub/sub with an optional deferred queue."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[Event], None]]] = {}
        self._queue: deque[Event] = deque()

    def subscribe(self, event_name: str, handler: Callable[[Event], None]) -> None:
        self._subscribers.setdefault(event_name, []).append(handler)

    def unsubscribe(self, event_name: str, handler: Callable[[Event], None]) -> None:
        handlers = self._subscribers.get(event_name)
        if handlers and handler in handlers:
            handlers.remove(handler)

    def publish(self, name: str, **payload: Any) -> None:
        """Dispatch immediately to all subscribers of ``name``."""
        self._dispatch(Event(name=name, payload=dict(payload)))

    def publish_deferred(self, name: str, **payload: Any) -> None:
        """Queue the event; delivered on the next :meth:`pump` call."""
        self._queue.append(Event(name=name, payload=dict(payload)))

    def pump(self) -> int:
        """Dispatch all queued events. Returns how many were delivered."""
        delivered = 0
        while self._queue:
            self._dispatch(self._queue.popleft())
            delivered += 1
        return delivered

    def clear(self) -> None:
        self._subscribers.clear()
        self._queue.clear()

    def _dispatch(self, event: Event) -> None:
        for handler in list(self._subscribers.get(event.name, [])):
            try:
                handler(event)
            except Exception:  # one bad listener must not break the others
                _logger.exception("Event handler failed for '%s'", event.name)
