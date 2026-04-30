"""Protect event serializers.

``EventManager.list_events`` / ``get_event`` return plain dicts shaped by
``_event_to_dict``. Phase 4A PR2 Cluster 2 adds:

  - ``EventDetailSerializer`` (``protect_get_event``) — same shape as the LIST
    serializer, registered as DETAIL.
  - ``EventThumbnailSerializer`` (``protect_get_event_thumbnail``) — manager
    returns ``{event_id, thumbnail_id, thumbnail_available, image_base64?,
    content_type?, message?}``. Pass-through with normalised keys.
  - ``RecentEventsSerializer`` (``protect_recent_events``) — the tool layer
    has already wrapped buffer reads as ``{events, count, source, buffer_size}``;
    we expose this as DETAIL pass-through (the wrapper *is* the payload).
  - ``SmartDetectionsSerializer`` (``protect_list_smart_detections``) — list
    of event dicts; EVENT_LOG kind, identical to the events serializer.
  - ``ProtectStreamSubscriptionSerializer`` (``protect_subscribe_events``) —
    STREAM kind. Returns ``{stream_url, transport: "sse", buffer_size,
    instructions}`` so MCP consumers can discover the rich-API stream
    surface; rich-API clients connect to ``GET /v1/streams/protect/events``.
  - ``EventMutationAckSerializer`` (``protect_acknowledge_event``) — DETAIL
    pass-through (manager returns a preview dict).
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _event_payload(obj) -> dict:
    return {
        "id": _get(obj, "id"),
        "type": _get(obj, "type"),
        "start": _get(obj, "start"),
        "end": _get(obj, "end"),
        "score": _get(obj, "score"),
        "smart_detect_types": _get(obj, "smart_detect_types") or [],
        "camera": _get(obj, "camera_id"),
        "thumbnail": _get(obj, "thumbnail_id"),
    }


@register_serializer(
    tools={
        "protect_list_events": {"kind": RenderKind.EVENT_LOG},
    },
    resources=[
        (("protect", "events"), {"kind": RenderKind.EVENT_LOG}),
    ],
)
class EventSerializer(Serializer):
    kind = RenderKind.EVENT_LOG
    primary_key = "id"
    display_columns = ["type", "start", "score"]
    sort_default = "start:desc"

    @staticmethod
    def serialize(obj) -> dict:
        return _event_payload(obj)


@register_serializer(tools={"protect_get_event": {"kind": RenderKind.DETAIL}})
class EventDetailSerializer(Serializer):
    """Single-event detail; mirrors ``EventSerializer`` payload."""

    @staticmethod
    def serialize(obj) -> dict:
        return _event_payload(obj)


@register_serializer(tools={"protect_get_event_thumbnail": {"kind": RenderKind.DETAIL}})
class EventThumbnailSerializer(Serializer):
    """Manager returns a dict with ``image_base64`` (decoded) or fallback message."""

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, dict):
            return {
                "event_id": obj.get("event_id"),
                "thumbnail_id": obj.get("thumbnail_id"),
                "thumbnail_available": obj.get("thumbnail_available", False),
                "image_base64": obj.get("image_base64"),
                "content_type": obj.get("content_type"),
                "message": obj.get("message"),
                "url": obj.get("url"),
            }
        if isinstance(obj, (bytes, bytearray)):
            # Defensive — manager today returns a dict, but if a future
            # revision passes raw JPEG bytes through, surface metadata.
            return {
                "event_id": None,
                "thumbnail_available": True,
                "size_bytes": len(obj),
                "content_type": "image/jpeg",
            }
        return {"event_id": None, "thumbnail_available": False, "result": str(obj)}


@register_serializer(tools={"protect_list_smart_detections": {"kind": RenderKind.EVENT_LOG}})
class SmartDetectionsSerializer(Serializer):
    """List of event dicts (same shape as ``EventSerializer``); EVENT_LOG."""

    kind = RenderKind.EVENT_LOG
    primary_key = "id"
    display_columns = ["type", "start", "score", "smart_detect_types"]
    sort_default = "start:desc"

    @staticmethod
    def serialize(obj) -> dict:
        return _event_payload(obj)


@register_serializer(tools={"protect_recent_events": {"kind": RenderKind.DETAIL}})
class RecentEventsSerializer(Serializer):
    """The tool layer already wraps buffer reads as
    ``{events, count, source, buffer_size}``. Pass-through DETAIL — the
    wrapper *is* the payload, so we surface it as-is rather than treating
    it as a list (renderers that want per-event rows can read ``data.events``).
    """

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, dict):
            return obj
        if isinstance(obj, list):
            return {"events": obj, "count": len(obj)}
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"result": str(obj)}


@register_serializer(tools={"protect_subscribe_events": {"kind": RenderKind.STREAM}})
class ProtectStreamSubscriptionSerializer(Serializer):
    """Phase 4B: returns the SSE URL where live events are streamed.

    The MCP tool call exposes this metadata so consumers can discover the
    rich-API stream surface; rich-API clients connect to
    ``GET /v1/streams/protect/events``.
    """

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, dict):
            return {
                "stream_url": "/v1/streams/protect/events",
                "transport": "sse",
                "buffer_size": obj.get("buffer_size"),
                "instructions": obj.get("instructions"),
            }
        return {"stream_url": "/v1/streams/protect/events", "transport": "sse"}


@register_serializer(tools={"protect_acknowledge_event": {"kind": RenderKind.DETAIL}})
class EventMutationAckSerializer(Serializer):
    """Pass-through ack for ``protect_acknowledge_event`` preview dict."""

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"result": str(obj)}
