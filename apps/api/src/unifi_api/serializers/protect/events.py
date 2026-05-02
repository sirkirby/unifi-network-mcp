"""Protect event mutation + stream serializers.

Phase 6 PR3 Task B — read serializers (``EventSerializer``,
``EventDetailSerializer``, ``EventThumbnailSerializer``,
``SmartDetectionsSerializer``) moved to Strawberry types in
``unifi_api.graphql.types.protect.events``. Their tools
(``protect_list_events``, ``protect_get_event``,
``protect_get_event_thumbnail``, ``protect_list_smart_detections``) are
listed in ``PHASE6_TYPE_MIGRATED_TOOLS`` and dispatched via the
type_registry.

Three serializers stay here because they cannot move to a typed read
surface without rewriting the SSE stream generator or the mutation ack
flow:

  - ``RecentEventsSerializer`` (``protect_recent_events``) — DETAIL
    pass-through for the buffer-snapshot wrapper. ``routes/streams/protect.py``
    calls ``serializer.serialize`` directly per broadcast event, so the
    serializer must remain dict-shaped.
  - ``ProtectStreamSubscriptionSerializer`` (``protect_subscribe_events``) —
    STREAM kind shim that returns ``{stream_url, transport: "sse",
    buffer_size, instructions}``.
  - ``EventMutationAckSerializer`` (``protect_acknowledge_event``) —
    DETAIL pass-through ack for the preview dict.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


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
    def serialize(obj: Any) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"result": str(obj)}
