"""Event management for UniFi Access.

Provides:
- ``EventBuffer`` -- ring buffer for recent Access events received via websocket
- ``EventManager`` -- domain logic for querying, filtering, and streaming events
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# EventBuffer
# ---------------------------------------------------------------------------


class EventBuffer:
    """Ring buffer for recent Access events.

    Events are stored as plain dicts with a ``_buffered_at`` timestamp for
    TTL-based lazy expiration.  The buffer is capped at *max_size* entries;
    once full the oldest entry is silently dropped.

    Thread-safety note: ``deque(maxlen=N)`` is thread-safe for single-producer
    appends on CPython, which matches our use-case (one websocket callback).
    """

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300) -> None:
        self._buffer: deque[dict[str, Any]] = deque(maxlen=max_size)
        self._ttl = ttl_seconds

    def add(self, event: dict[str, Any]) -> None:
        """Add *event* to the buffer, stamping it with the current time."""
        event["_buffered_at"] = time.time()
        self._buffer.append(event)

    def get_recent(
        self,
        event_type: str | None = None,
        door_id: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return recent events matching the supplied filters.

        Events older than the configured TTL are silently skipped (lazy
        expiration).  Results are returned newest-first.
        """
        cutoff = time.time() - self._ttl
        results: list[dict[str, Any]] = []
        for event in reversed(self._buffer):
            if event.get("_buffered_at", 0) < cutoff:
                continue
            if event_type and event.get("type") != event_type:
                continue
            if door_id and event.get("door_id") != door_id:
                continue
            results.append(event)
            if limit and len(results) >= limit:
                break
        return results

    def clear(self) -> None:
        """Remove all events from the buffer."""
        self._buffer.clear()

    def __len__(self) -> int:
        return len(self._buffer)


# ---------------------------------------------------------------------------
# EventManager
# ---------------------------------------------------------------------------


class EventManager:
    """Domain logic for UniFi Access events.

    Responsibilities:
    - Websocket subscription (when implemented)
    - Event parsing and buffering
    - REST-based event queries
    """

    def __init__(self, connection_manager: Any, config: dict[str, Any] | None = None) -> None:
        cfg = config or {}
        self._cm = connection_manager
        self._buffer = EventBuffer(
            max_size=int(cfg.get("buffer_size", 100)),
            ttl_seconds=int(cfg.get("buffer_ttl_seconds", 300)),
        )
        self._server: Any | None = None  # FastMCP server reference for future notifications

    # ------------------------------------------------------------------
    # Server / notification wiring
    # ------------------------------------------------------------------

    def set_server(self, server: Any) -> None:
        """Store a reference to the FastMCP server for future notification support."""
        self._server = server

    # ------------------------------------------------------------------
    # Buffer access
    # ------------------------------------------------------------------

    def get_recent_from_buffer(
        self,
        event_type: str | None = None,
        door_id: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return recent events from the websocket ring buffer."""
        return self._buffer.get_recent(
            event_type=event_type,
            door_id=door_id,
            limit=limit,
        )

    @property
    def buffer_size(self) -> int:
        """Current number of events in the buffer."""
        return len(self._buffer)

    # ------------------------------------------------------------------
    # REST API queries (stubs)
    # ------------------------------------------------------------------

    async def list_events(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Query events from the Access controller via REST API."""
        raise NotImplementedError("EventManager.list_events not yet implemented")

    async def get_event(self, event_id: str) -> dict[str, Any]:
        """Get a single event by ID."""
        raise NotImplementedError("EventManager.get_event not yet implemented")
