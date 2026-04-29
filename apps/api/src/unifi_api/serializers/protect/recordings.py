"""Protect recording serializers.

``RecordingManager.list_recordings`` returns a single dict describing the
available recording window for a camera (uiprotect does not expose
discrete segments). The serializer flattens the keys we surface in lists.

Note: there is no ``protect_get_recording`` tool in the protect manifest;
only ``protect_list_recordings`` exists, so we register LIST only and
expose the resource as both a list path and a detail path so the
catalog can surface a per-id link if a future tool is added.

Phase 4A PR2 Cluster 2 adds:

  - ``RecordingStatusSerializer`` (``protect_get_recording_status``) — manager
    returns ``{cameras: [...], count}``. Pass-through DETAIL.
  - ``RecordingMutationAckSerializer`` (``protect_delete_recording``,
    ``protect_export_clip``) — DETAIL pass-through with bool fallback.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


@register_serializer(
    tools={
        "protect_list_recordings": {"kind": RenderKind.LIST},
    },
    resources=[
        (("protect", "recordings"), {"kind": RenderKind.LIST}),
        (("protect", "recordings/{id}"), {"kind": RenderKind.DETAIL}),
    ],
)
class RecordingSerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "id"
    display_columns = ["type", "start", "end", "file_size"]
    sort_default = "start:desc"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "id"),
            "type": _get(obj, "type"),
            "camera": _get(obj, "camera_id"),
            "start": _get(obj, "start"),
            "end": _get(obj, "end"),
            "file_size": _get(obj, "file_size"),
        }


@register_serializer(tools={"protect_get_recording_status": {"kind": RenderKind.DETAIL}})
class RecordingStatusSerializer(Serializer):
    """Manager returns ``{cameras: [...], count}`` — pass through normalised."""

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, dict):
            return {
                "cameras": obj.get("cameras") or [],
                "count": obj.get("count", len(obj.get("cameras") or [])),
            }
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"cameras": [], "count": 0}


@register_serializer(
    tools={
        "protect_delete_recording": {"kind": RenderKind.DETAIL},
        "protect_export_clip": {"kind": RenderKind.DETAIL},
    },
)
class RecordingMutationAckSerializer(Serializer):
    """Pass-through ack for recording mutations. Bool fallback for completeness."""

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"result": str(obj)}
