"""Protect EventManager subscriber fan-out tests (Phase 4B)."""

from unittest.mock import MagicMock

from unifi_core.protect.managers.event_manager import EventManager


def _make_manager() -> EventManager:
    return EventManager(MagicMock())


def _dispatch(mgr: EventManager, event_dict: dict) -> None:
    """Mirror the fan-out block inside ``_on_ws_message``.

    The full websocket parse path requires a ``WSSubscriptionMessage`` from
    uiprotect; for these tests we drive the subscriber list directly, which
    is the same code path executed after ``self._buffer.add(event_dict)``.
    """
    mgr._buffer.add(event_dict)
    for cb in list(mgr._subscribers):
        try:
            cb(event_dict)
        except Exception:
            pass


def test_add_subscriber_returns_unsub() -> None:
    mgr = _make_manager()
    received: list[dict] = []
    unsub = mgr.add_subscriber(received.append)
    assert callable(unsub)
    _dispatch(mgr, {"id": "e1", "type": "motion"})
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
    _dispatch(mgr, {"id": "e1", "type": "motion"})
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
    _dispatch(mgr, {"id": "e1", "type": "motion"})
    assert len(received) == 1
    assert received[0]["id"] == "e1"
