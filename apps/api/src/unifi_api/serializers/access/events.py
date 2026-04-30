"""Access event serializers.

``EventManager.list_events`` / ``get_recent_from_buffer`` return
``list[dict[str, Any]]`` — registered as EVENT_LOG.
``EventManager.get_event`` returns a single dict — registered as DETAIL.
``EventManager.get_activity_summary`` returns the histogram payload from
``activities/histogram`` (a dict) — DETAIL pass-through with normalised
fields.

The ``access_subscribe_events`` tool now uses STREAM kind via
``AccessStreamSubscriptionSerializer``: it returns
``{stream_url, transport: "sse", buffer_size, instructions}`` so MCP
consumers can discover the rich-API stream surface; rich-API clients
connect to ``GET /v1/streams/access/events``.
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
        "timestamp": _get(obj, "timestamp") or _get(obj, "time"),
        "door_id": _get(obj, "door_id"),
        "user_id": _get(obj, "user_id"),
        "credential_id": _get(obj, "credential_id"),
        "result": _get(obj, "result"),
    }


@register_serializer(
    tools={
        "access_list_events": {"kind": RenderKind.EVENT_LOG},
        "access_recent_events": {"kind": RenderKind.EVENT_LOG},
    },
    resources=[
        (("access", "events"), {"kind": RenderKind.EVENT_LOG}),
    ],
)
class AccessEventSerializer(Serializer):
    kind = RenderKind.EVENT_LOG
    primary_key = "id"
    display_columns = ["type", "timestamp", "door_id", "user_id", "result"]
    sort_default = "timestamp:desc"

    @staticmethod
    def serialize(obj) -> dict:
        return _event_payload(obj)


@register_serializer(tools={"access_get_event": {"kind": RenderKind.DETAIL}})
class EventDetailSerializer(Serializer):
    """Single-event detail; mirrors ``AccessEventSerializer`` payload."""

    kind = RenderKind.DETAIL

    @staticmethod
    def serialize(obj) -> dict:
        return _event_payload(obj)


@register_serializer(tools={"access_get_activity_summary": {"kind": RenderKind.DETAIL}})
class ActivitySummarySerializer(Serializer):
    """Activity histogram summary (``activities/histogram`` payload).

    Manager passes through the controller's response shape; we surface
    catalog-level fields with ``None`` fallbacks when keys are absent.
    """

    kind = RenderKind.DETAIL

    @staticmethod
    def serialize(obj) -> dict:
        if not isinstance(obj, dict):
            if hasattr(obj, "model_dump"):
                obj = obj.model_dump()
            else:
                return {"result": str(obj)}
        return {
            "period_start": obj.get("period_start") or obj.get("since"),
            "period_end": obj.get("period_end") or obj.get("until"),
            "total_events": obj.get("total_events") or obj.get("total"),
            "granted_count": obj.get("granted_count"),
            "denied_count": obj.get("denied_count"),
            "top_users": obj.get("top_users"),
            "buckets": obj.get("buckets") or obj.get("histogram"),
        }


@register_serializer(tools={"access_subscribe_events": {"kind": RenderKind.STREAM}})
class AccessStreamSubscriptionSerializer(Serializer):
    """Phase 4B: returns the SSE URL where live events are streamed.

    The MCP tool call exposes this metadata so consumers can discover the
    rich-API stream surface; rich-API clients connect to
    ``GET /v1/streams/access/events``.
    """

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, dict):
            return {
                "stream_url": "/v1/streams/access/events",
                "transport": "sse",
                "buffer_size": obj.get("buffer_size"),
                "instructions": obj.get("instructions"),
            }
        return {"stream_url": "/v1/streams/access/events", "transport": "sse"}
