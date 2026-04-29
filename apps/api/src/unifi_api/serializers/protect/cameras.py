"""Protect camera serializer.

Manager methods (``CameraManager.list_cameras`` / ``get_camera``) return
plain dicts shaped by ``_format_camera_summary`` and the detail merge in
``get_camera``. We read dict keys directly; if a Pydantic-like object is
ever passed, fall back to attribute access via ``_get``.
"""

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
