"""Tests for core.events (infrastructure only)."""

from __future__ import annotations

from core.events import EventBus


def test_publish_delivers_payload() -> None:
    received = []
    bus = EventBus()
    bus.subscribe("thing", received.append)
    bus.publish("thing", value=42)
    assert len(received) == 1
    assert received[0].name == "thing"
    assert received[0].payload == {"value": 42}


def test_unsubscribe_stops_delivery() -> None:
    received = []
    bus = EventBus()
    bus.subscribe("thing", received.append)
    bus.unsubscribe("thing", received.append)
    bus.publish("thing")
    assert received == []


def test_deferred_events_wait_for_pump() -> None:
    received = []
    bus = EventBus()
    bus.subscribe("thing", received.append)
    bus.publish_deferred("thing")
    assert received == []
    assert bus.pump() == 1
    assert len(received) == 1


def test_failing_handler_does_not_break_others() -> None:
    received = []
    bus = EventBus()

    def bad(_event: object) -> None:
        raise RuntimeError("boom")

    bus.subscribe("thing", bad)
    bus.subscribe("thing", received.append)
    bus.publish("thing")  # must not raise
    assert len(received) == 1
