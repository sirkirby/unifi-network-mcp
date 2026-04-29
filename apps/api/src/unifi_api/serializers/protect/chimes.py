"""Protect chime serializer (Phase 4A PR2 Cluster 1).

``ChimeManager.list_chimes`` returns plain dicts shaped by
``_format_chime_summary`` — fields include ``id``, ``mac`` (omitted by the
helper, but tolerated), ``name``, ``state``, ``camera_ids``,
``ring_settings``, ``available_tracks``. We expose a LIST view with the
fields most useful for tabular renderers; ``camera_ids`` is renamed to
``paired_cameras`` per the spec.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


@register_serializer(
    tools={
        "protect_list_chimes": {"kind": RenderKind.LIST},
    },
    resources=[
        (("protect", "chimes"), {"kind": RenderKind.LIST}),
    ],
)
class ChimeSerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "id"
    display_columns = ["name", "model", "state", "volume"]

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "id"),
            "mac": _get(obj, "mac"),
            "name": _get(obj, "name"),
            "model": _get(obj, "model"),
            "type": _get(obj, "type"),
            "state": _get(obj, "state"),
            "is_connected": _get(obj, "is_connected"),
            "firmware_version": _get(obj, "firmware_version"),
            "volume": _get(obj, "volume"),
            "paired_cameras": _get(obj, "camera_ids") or [],
            "ring_settings": _get(obj, "ring_settings") or [],
            "available_tracks": _get(obj, "available_tracks") or [],
        }
