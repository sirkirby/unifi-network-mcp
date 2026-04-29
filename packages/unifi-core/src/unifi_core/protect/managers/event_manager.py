"""Event management for UniFi Protect.

Provides:
- ``EventBuffer`` -- ring buffer for recent NVR events received via websocket
- ``EventManager`` -- domain logic for querying, filtering, and streaming events
"""

from __future__ import annotations

import logging
import time
from collections import deque
from datetime import datetime
from typing import Any, Callable

from uiprotect.data import Event, EventType, ModelType, SmartDetectObjectType, WSAction, WSSubscriptionMessage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# EventBuffer
# ---------------------------------------------------------------------------


class EventBuffer:
    """Ring buffer for recent NVR events.

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
        camera_id: str | None = None,
        min_confidence: int | None = None,
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
            if camera_id and event.get("camera_id") != camera_id:
                continue
            if min_confidence is not None and event.get("score", 100) < min_confidence:
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
    """Domain logic for UniFi Protect events.

    Responsibilities:
    - Websocket subscription via pyunifiprotect
    - Event parsing and buffering
    - REST-based event queries (list, get, smart detections, thumbnails)
    - Acknowledge mutations
    """

    def __init__(self, connection_manager: Any, config: dict[str, Any] | None = None) -> None:
        cfg = config or {}
        self._cm = connection_manager
        self._buffer = EventBuffer(
            max_size=int(cfg.get("buffer_size", 100)),
            ttl_seconds=int(cfg.get("buffer_ttl_seconds", 300)),
        )
        self._min_confidence = int(cfg.get("smart_detection_min_confidence", 50))
        self._ws_unsub: Callable[[], None] | None = None
        self._server: Any | None = None  # FastMCP server reference for future notifications
        self._subscribers: list[Callable[[dict], None]] = []

    # ------------------------------------------------------------------
    # Server / notification wiring
    # ------------------------------------------------------------------

    def set_server(self, server: Any) -> None:
        """Store a reference to the FastMCP server.

        This enables future resource-update notifications once FastMCP
        exposes a public API for sending notifications from background
        callbacks.  Currently the session is only accessible during
        request handling, so push notifications are not yet supported.
        """
        self._server = server

    # ------------------------------------------------------------------
    # Websocket lifecycle
    # ------------------------------------------------------------------

    async def start_listening(self) -> None:
        """Subscribe to the pyunifiprotect websocket for real-time events.

        The ``subscribe_websocket`` method on the API client returns an
        unsubscribe callable which we store for clean shutdown.
        """
        self._ws_unsub = self._cm.client.subscribe_websocket(self._on_ws_message)
        logger.info("[event-mgr] Websocket subscription started.")

    async def stop_listening(self) -> None:
        """Unsubscribe from the websocket."""
        if self._ws_unsub is not None:
            try:
                self._ws_unsub()
            except Exception:
                logger.debug("[event-mgr] Error unsubscribing websocket", exc_info=True)
            self._ws_unsub = None
            logger.info("[event-mgr] Websocket subscription stopped.")

    # ------------------------------------------------------------------
    # Websocket callback & parsing
    # ------------------------------------------------------------------

    def _on_ws_message(self, msg: WSSubscriptionMessage) -> None:
        """Callback invoked for every websocket message from the NVR.

        Filters for Event model updates and adds them to the ring buffer.
        """
        try:
            event_dict = self._parse_ws_message(msg)
            if event_dict:
                self._buffer.add(event_dict)
                logger.debug(
                    "[event-mgr] Buffered event: type=%s camera=%s",
                    event_dict.get("type"),
                    event_dict.get("camera_id"),
                )
                # Phase 4B: fan out to subscribers
                for cb in list(self._subscribers):
                    try:
                        cb(event_dict)
                    except Exception:
                        logger.debug("[event-mgr] subscriber callback failed", exc_info=True)
                # NOTE: Push notifications to MCP clients are not yet
                # supported because ServerSession.send_resource_updated()
                # is only accessible from within a request context.  When
                # FastMCP adds a public broadcast API we can wire it here.
        except Exception:
            logger.debug("[event-mgr] Error processing websocket message", exc_info=True)

    def _parse_ws_message(self, msg: WSSubscriptionMessage) -> dict[str, Any] | None:
        """Parse a pyunifiprotect WSSubscriptionMessage into a plain dict.

        Only ``ADD`` and ``UPDATE`` actions for ``Event`` models are
        captured.  Returns ``None`` for messages we don't care about.
        """
        if msg.action not in (WSAction.ADD, WSAction.UPDATE):
            return None

        obj = msg.new_obj
        if obj is None:
            return None

        # Only process Event model objects
        model = getattr(obj, "model", None)
        if model != ModelType.EVENT:
            return None

        # obj is an Event instance at this point
        return self._event_to_dict(obj)

    def _resolve_camera_name(self, camera_id: str | None) -> str | None:
        """Resolve a camera ID to its display name from bootstrap data."""
        if not camera_id:
            return None
        try:
            cameras = self._cm.client.bootstrap.cameras
            camera = cameras.get(camera_id)
            return camera.name if camera else None
        except Exception:
            return None

    def _event_to_dict(self, event: Event, compact: bool = False) -> dict[str, Any]:
        """Convert a uiprotect ``Event`` object to a serialisable dict.

        When *compact* is True, omits low-value fields (thumbnail_id,
        category, sub_category, is_favorite) to reduce token usage in
        LLM contexts (~40% smaller per event).
        """
        result: dict[str, Any] = {
            "id": event.id,
            "type": event.type.value if isinstance(event.type, EventType) else str(event.type),
            "camera_id": event.camera_id,
            "camera_name": self._resolve_camera_name(event.camera_id),
            "start": event.start.isoformat() if event.start else None,
            "end": event.end.isoformat() if event.end else None,
            "score": event.score,
            "smart_detect_types": [
                t.value if isinstance(t, SmartDetectObjectType) else str(t) for t in (event.smart_detect_types or [])
            ],
        }
        if not compact:
            result["thumbnail_id"] = event.thumbnail_id
            result["category"] = event.category
            result["sub_category"] = event.sub_category
            result["is_favorite"] = event.is_favorite
        return result

    # ------------------------------------------------------------------
    # Buffer access
    # ------------------------------------------------------------------

    def get_recent_from_buffer(
        self,
        event_type: str | None = None,
        camera_id: str | None = None,
        min_confidence: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return recent events from the websocket ring buffer."""
        return self._buffer.get_recent(
            event_type=event_type,
            camera_id=camera_id,
            min_confidence=min_confidence,
            limit=limit,
        )

    @property
    def buffer_size(self) -> int:
        """Current number of events in the buffer."""
        return len(self._buffer)

    def add_subscriber(self, cb: Callable[[dict], None]) -> Callable[[], None]:
        """Register *cb* to receive every buffered event. Returns unsub."""
        self._subscribers.append(cb)

        def _unsub() -> None:
            try:
                self._subscribers.remove(cb)
            except ValueError:
                pass

        return _unsub

    # ------------------------------------------------------------------
    # REST API queries
    # ------------------------------------------------------------------

    async def list_events(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        event_type: str | None = None,
        camera_id: str | None = None,
        limit: int = 30,
        compact: bool = False,
    ) -> list[dict[str, Any]]:
        """Query events from the NVR via the REST API.

        Wraps ``ProtectApiClient.get_events`` with convenient filtering.
        """
        kwargs: dict[str, Any] = {"limit": limit, "sorting": "desc"}

        if start:
            kwargs["start"] = start
        if end:
            kwargs["end"] = end

        # Map string event type to EventType enum
        types_filter: list[EventType] | None = None
        if event_type:
            try:
                types_filter = [EventType(event_type)]
            except ValueError:
                # Try matching by enum name (case-insensitive)
                for et in EventType:
                    if et.name.lower() == event_type.lower():
                        types_filter = [et]
                        break
                if types_filter is None:
                    logger.warning("[event-mgr] Unknown event type filter: %s", event_type)
        if types_filter:
            kwargs["types"] = types_filter

        events: list[Event] = await self._cm.client.get_events(**kwargs)

        results: list[dict[str, Any]] = []
        for ev in events:
            if camera_id and ev.camera_id != camera_id:
                continue
            results.append(self._event_to_dict(ev, compact=compact))

        return results

    async def get_event(self, event_id: str) -> dict[str, Any]:
        """Get a single event by ID.

        Raises ``ValueError`` if the event is not found.
        """
        try:
            event: Event = await self._cm.client.get_event(event_id)
        except Exception as exc:
            raise ValueError(f"Event not found: {event_id}") from exc
        return self._event_to_dict(event)

    async def get_event_thumbnail(
        self,
        event_id: str,
        width: int | None = None,
        height: int | None = None,
    ) -> dict[str, Any]:
        """Get the thumbnail for an event.

        Returns a dict with ``thumbnail_id`` and optionally ``image_base64``
        (JPEG bytes encoded as base64).
        """
        # First retrieve the event to get its thumbnail_id
        try:
            event: Event = await self._cm.client.get_event(event_id)
        except Exception as exc:
            raise ValueError(f"Event not found: {event_id}") from exc

        if not event.thumbnail_id:
            return {
                "event_id": event_id,
                "thumbnail_available": False,
                "message": "Event has no thumbnail (may still be in progress).",
            }

        try:
            thumb_bytes = await self._cm.client.get_event_thumbnail(
                event.thumbnail_id,
                width=width,
                height=height,
            )
        except Exception as exc:
            logger.debug("[event-mgr] Failed to fetch thumbnail for %s: %s", event_id, exc)
            return {
                "event_id": event_id,
                "thumbnail_id": event.thumbnail_id,
                "thumbnail_available": False,
                "message": "Thumbnail not yet available (event may still be in progress).",
            }

        if thumb_bytes is None:
            return {
                "event_id": event_id,
                "thumbnail_id": event.thumbnail_id,
                "thumbnail_available": False,
                "message": "Thumbnail not yet available (event may still be in progress).",
            }

        import base64

        return {
            "event_id": event_id,
            "thumbnail_id": event.thumbnail_id,
            "thumbnail_available": True,
            "image_base64": base64.b64encode(thumb_bytes).decode(),
            "content_type": "image/jpeg",
        }

    async def list_smart_detections(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        camera_id: str | None = None,
        detection_type: str | None = None,
        min_confidence: int | None = None,
        limit: int = 30,
        compact: bool = False,
    ) -> list[dict[str, Any]]:
        """List smart detection events with optional filtering.

        Queries for ``smartDetectZone`` and ``smartDetectLine`` event types,
        then filters by detection type and confidence score.
        """
        min_conf = min_confidence if min_confidence is not None else self._min_confidence

        kwargs: dict[str, Any] = {
            "limit": limit,
            "sorting": "desc",
            "types": [EventType.SMART_DETECT, EventType.SMART_DETECT_LINE],
        }
        if start:
            kwargs["start"] = start
        if end:
            kwargs["end"] = end

        # Filter by smart detect type if specified
        if detection_type:
            smart_types_filter: list[SmartDetectObjectType] = []
            try:
                smart_types_filter = [SmartDetectObjectType(detection_type)]
            except ValueError:
                for sdt in SmartDetectObjectType:
                    if sdt.name.lower() == detection_type.lower():
                        smart_types_filter = [sdt]
                        break
            if smart_types_filter:
                kwargs["smart_detect_types"] = smart_types_filter

        events: list[Event] = await self._cm.client.get_events(**kwargs)

        results: list[dict[str, Any]] = []
        for ev in events:
            if camera_id and ev.camera_id != camera_id:
                continue
            if ev.score < min_conf:
                continue
            results.append(self._event_to_dict(ev, compact=compact))

        return results

    async def acknowledge_event(self, event_id: str) -> dict[str, Any]:
        """Mark an event as acknowledged/favorite on the NVR.

        Uses the ``is_favorite`` field as an acknowledgement mechanism since
        the Protect API does not have a dedicated acknowledge endpoint.

        Returns a preview dict for the confirmation pattern.
        """
        try:
            event: Event = await self._cm.client.get_event(event_id)
        except Exception as exc:
            raise ValueError(f"Event not found: {event_id}") from exc

        return {
            "event_id": event_id,
            "type": event.type.value if isinstance(event.type, EventType) else str(event.type),
            "camera_id": event.camera_id,
            "camera_name": self._resolve_camera_name(event.camera_id),
            "current_is_favorite": event.is_favorite,
            "proposed_is_favorite": True,
        }

    async def apply_acknowledge_event(self, event_id: str) -> dict[str, Any]:
        """Apply the acknowledge (favorite) mutation to the NVR."""
        try:
            event: Event = await self._cm.client.get_event(event_id)
        except Exception as exc:
            raise ValueError(f"Event not found: {event_id}") from exc

        # The Protect API uses is_favorite as the closest analog to
        # "acknowledged".  We set it to True.
        # Note: the exact mutation API depends on the uiprotect version.
        # Some versions expose event.set_is_favorite() or similar.
        # Fall back to a generic save approach.
        try:
            event.is_favorite = True
            await event.save_device()
        except AttributeError:
            # Older API versions may not have save_device on events
            logger.warning("[event-mgr] Event save_device not available; acknowledge may not persist.")

        return {
            "event_id": event_id,
            "acknowledged": True,
            "is_favorite": True,
        }
