"""Protect camera serializers (Phase 4A PR2 Cluster 1).

Manager methods (``CameraManager.list_cameras`` / ``get_camera``) return
plain dicts shaped by ``_format_camera_summary`` and the detail merge in
``get_camera``. We read dict keys directly; if a Pydantic-like object is
ever passed, fall back to attribute access via ``_get``.

Phase 4A PR2 Cluster 1 adds:
  - CameraAnalyticsSerializer (``protect_get_camera_analytics``)
  - CameraStreamsSerializer (``protect_get_camera_streams``)
  - SnapshotSerializer (``protect_get_snapshot``) — manager returns raw
    bytes, so we expose ``{size_bytes, content_type, captured_at}``.
  - CameraMutationAckSerializer (PTZ/reboot/toggle/update preview tools)
"""

from datetime import datetime, timezone
from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


@register_serializer(
    tools={
        "protect_list_cameras": {"kind": RenderKind.LIST},
        "protect_get_camera": {"kind": RenderKind.DETAIL},
    },
    resources=[
        (("protect", "cameras"), {"kind": RenderKind.LIST}),
        (("protect", "cameras/{id}"), {"kind": RenderKind.DETAIL}),
    ],
)
class CameraSerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "id"
    display_columns = ["name", "model", "state", "is_recording"]

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "id"),
            "mac": _get(obj, "mac"),
            "name": _get(obj, "name"),
            "model": _get(obj, "model"),
            "type": _get(obj, "type"),
            "state": _get(obj, "state"),
            "is_recording": _get(obj, "is_recording"),
            "is_motion_detected": _get(obj, "is_motion_detected"),
            "is_smart_detected": _get(obj, "is_smart_detected"),
            "host": _get(obj, "ip_address") or _get(obj, "host"),
            "channels": _get(obj, "channels") or [],
        }


@register_serializer(tools={"protect_get_camera_analytics": {"kind": RenderKind.DETAIL}})
class CameraAnalyticsSerializer(Serializer):
    """Manager returns a flat-ish dict; pass through with normalised keys."""

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "camera_id": _get(obj, "camera_id"),
            "camera_name": _get(obj, "camera_name"),
            "detections": _get(obj, "detections") or {},
            "smart_detects": _get(obj, "smart_detects") or {},
            "smart_audio_detects": _get(obj, "smart_audio_detects") or {},
            "currently_detected": _get(obj, "currently_detected") or {},
            "motion_zone_count": _get(obj, "motion_zone_count", 0),
            "smart_detect_zone_count": _get(obj, "smart_detect_zone_count", 0),
            "stats": _get(obj, "stats") or {},
        }


@register_serializer(tools={"protect_get_camera_streams": {"kind": RenderKind.DETAIL}})
class CameraStreamsSerializer(Serializer):
    """Manager returns ``{camera_id, camera_name, channels: {name: {..}}, rtsps_streams: {...}}``."""

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "camera_id": _get(obj, "camera_id"),
            "camera_name": _get(obj, "camera_name"),
            "channels": _get(obj, "channels") or {},
            "rtsps_streams": _get(obj, "rtsps_streams") or {},
        }


@register_serializer(tools={"protect_get_snapshot": {"kind": RenderKind.DETAIL}})
class SnapshotSerializer(Serializer):
    """Manager returns raw JPEG ``bytes``. Surface metadata only — the binary
    body is encoded by the tool layer separately."""

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, (bytes, bytearray)):
            return {
                "size_bytes": len(obj),
                "content_type": "image/jpeg",
                "captured_at": datetime.now(timezone.utc).isoformat(),
            }
        if isinstance(obj, dict):
            return {
                "size_bytes": obj.get("size_bytes"),
                "content_type": obj.get("content_type", "image/jpeg"),
                "captured_at": obj.get("captured_at"),
                "url": obj.get("url"),
            }
        return {"size_bytes": None, "content_type": None, "captured_at": None}


@register_serializer(
    tools={
        "protect_ptz_move": {"kind": RenderKind.DETAIL},
        "protect_ptz_preset": {"kind": RenderKind.DETAIL},
        "protect_ptz_zoom": {"kind": RenderKind.DETAIL},
        "protect_reboot_camera": {"kind": RenderKind.DETAIL},
        "protect_toggle_recording": {"kind": RenderKind.DETAIL},
        "protect_update_camera_settings": {"kind": RenderKind.DETAIL},
    },
)
class CameraMutationAckSerializer(Serializer):
    """Generic ack for camera-side mutations. Manager methods here return
    ``Dict[str, Any]`` (preview shape); bool fallback for completeness."""

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"result": str(obj)}
