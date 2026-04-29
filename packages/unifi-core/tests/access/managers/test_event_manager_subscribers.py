"""Access EventManager subscriber fan-out tests (Phase 4B)."""

from unittest.mock import MagicMock

from unifi_core.access.managers.event_manager import EventManager


def _make_manager() -> EventManager:
    return EventManager(MagicMock())


def _dispatch(mgr: EventManager, event_dict: dict) -> None:
    """Drive the fan-out path by invoking ``_on_event`` directly.

    ``_on_event`` is the buffer-add site for websocket events; passing a
    plain dict exercises the same code path that runs after
    ``self._buffer.add(event_data)`` in production.
    """
    mgr._on_event(event_dict)


def test_add_subscriber_returns_unsub() -> None:
    mgr = _make_manager()
    received: list[dict] = []
    unsub = mgr.add_subscriber(received.append)
    assert callable(unsub)
    _dispatch(mgr, {"id": "e1", "type": "door_open"})
    assert len(received) == 1
    assert received[0]["id"] == "e1"
    unsub()
    assert received[0] not in mgr._subscribers
    _dispatch(mgr, {"id": "e2"})
    assert len(received) == 1  # unsubscribed; no new events


def test_two_subscribers_both_receive_events() -> None:
    mgr = _make_manager()
    received_a: list[dict] = []
    received_b: list[dict] = []
    mgr.add_subscriber(received_a.append)
    mgr.add_subscriber(received_b.append)
    _dispatch(mgr, {"id": "e1", "type": "door_open"})
    assert len(received_a) == 1
    assert len(received_b) == 1
    assert received_a[0]["id"] == "e1"
    assert received_b[0]["id"] == "e1"


def test_subscriber_exception_isolated() -> None:
    mgr = _make_manager()

    def boom(_evt: dict) -> None:
        raise RuntimeError("oops")

    received: list[dict] = []
    mgr.add_subscriber(boom)
    mgr.add_subscriber(received.append)
    # Must not raise
    _dispatch(mgr, {"id": "e1", "type": "door_open"})
    assert len(received) == 1
    assert received[0]["id"] == "e1"
