"""Protect recording serializer.

``RecordingManager.list_recordings`` returns a single dict describing the
available recording window for a camera (uiprotect does not expose
discrete segments). The serializer flattens the keys we surface in lists.

Note: there is no ``protect_get_recording`` tool in the protect manifest;
only ``protect_list_recordings`` exists, so we register LIST only and
expose the resource as both a list path and a detail path so the
catalog can surface a per-id link if a future tool is added.
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
