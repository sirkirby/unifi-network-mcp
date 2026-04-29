"""Protect chime serializers.

``ChimeManager.list_chimes`` returns plain dicts shaped by
``_format_chime_summary`` — fields include ``id``, ``mac`` (omitted by the
helper, but tolerated), ``name``, ``state``, ``camera_ids``,
``ring_settings``, ``available_tracks``. We expose a LIST view with the
fields most useful for tabular renderers; ``camera_ids`` is renamed to
``paired_cameras`` per the spec.

Phase 4A PR2 Cluster 2 adds ``ChimeMutationAckSerializer`` for
``protect_trigger_chime`` and ``protect_update_chime``.
``ChimeManager.trigger_chime`` returns
``{chime_id, chime_name, triggered, volume, repeat_times}`` and
``update_chime`` returns
``{chime_id, chime_name, current_state, proposed_changes}``.
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


@register_serializer(
    tools={
        "protect_trigger_chime": {"kind": RenderKind.DETAIL},
        "protect_update_chime": {"kind": RenderKind.DETAIL},
    },
)
class ChimeMutationAckSerializer(Serializer):
    """Pass-through ack for chime trigger/update preview dicts."""

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"result": str(obj)}
