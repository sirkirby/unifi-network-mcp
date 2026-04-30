"""Event log serializers (Phase 4A PR1 Cluster 6).

Covers the EVENT_LOG kind for ``unifi_list_events``, ``unifi_get_alerts``,
``unifi_get_anomalies``, ``unifi_get_ips_events``. Each event entry is
serialized to a curated subset of fields:

- ``id`` (from ``_id``)
- ``key`` (event type, e.g. ``EVT_WU_Connected``)
- ``msg`` (human-readable description)
- ``severity`` (when present — alerts/IPS)
- ``time`` (epoch milliseconds)
- ``mac`` (associated client/device MAC)
- ``ip`` (associated IP, when present)

``sort_default = "time:desc"`` matches Phase 3's EVENT_LOG convention.
"""

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj, *keys):
    """Return the first non-None value among the listed keys."""
    if not isinstance(obj, dict):
        return None
    for k in keys:
        v = obj.get(k)
        if v is not None:
            return v
    return None


@register_serializer(
    tools={
        "unifi_list_events": {"kind": RenderKind.EVENT_LOG},
        "unifi_get_alerts": {"kind": RenderKind.EVENT_LOG},
        "unifi_get_anomalies": {"kind": RenderKind.EVENT_LOG},
        "unifi_get_ips_events": {"kind": RenderKind.EVENT_LOG},
    },
)
class EventLogSerializer(Serializer):
    """Curated event-log shape across UniFi event-style endpoints."""

    primary_key = "id"
    sort_default = "time:desc"
    display_columns = ["time", "key", "msg", "mac"]

    @staticmethod
    def serialize(record) -> dict:
        if not isinstance(record, dict):
            return {"id": None}
        out = {
            "id": _get(record, "_id", "id"),
            "key": _get(record, "key", "event_type", "type"),
            "msg": _get(record, "msg", "message", "description"),
            "time": _get(record, "time", "timestamp", "ts"),
            "mac": _get(record, "user", "mac", "ap", "ap_mac", "device_mac"),
            "ip": _get(record, "ip", "src_ip"),
        }
        sev = _get(record, "severity", "level")
        if sev is not None:
            out["severity"] = sev
        return out


@register_serializer(tools={"unifi_recent_events": {"kind": RenderKind.EVENT_LOG}})
class NetworkRecentEventsSerializer(EventLogSerializer):
    """unifi_recent_events emits the same per-event shape as unifi_list_events."""

    pass


@register_serializer(tools={"unifi_subscribe_events": {"kind": RenderKind.STREAM}})
class NetworkStreamSubscriptionSerializer(Serializer):
    """Phase 4B precursor — returns the SSE URL + buffer metadata.

    Replaces the Phase 4A handle pattern.
    """

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, dict):
            return {
                "stream_url": "/v1/streams/network/events",
                "transport": "sse",
                "buffer_size": obj.get("buffer_size"),
                "instructions": obj.get("instructions"),
            }
        return {"stream_url": "/v1/streams/network/events", "transport": "sse"}
