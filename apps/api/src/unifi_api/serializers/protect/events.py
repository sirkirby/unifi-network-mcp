"""Protect event serializer.

``EventManager.list_events`` returns plain dicts shaped by
``_event_to_dict``. Registered as EVENT_LOG kind.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


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
