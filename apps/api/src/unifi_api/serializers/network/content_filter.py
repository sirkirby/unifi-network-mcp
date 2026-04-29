"""Content filter serializers (Phase 4A PR1 Cluster 4).

``ContentFilterManager`` exposes ``get_content_filters()`` /
``get_content_filter_by_id()`` / ``update_content_filter()`` /
``delete_content_filter()`` on V2 ``/content-filtering``. The UniFi API
does not support creating new content filtering profiles (the controller
ships a fixed set); only update + delete mutations exist.

GET /content-filtering/{id} returns 405, so detail lookups are served by
list-then-filter at the manager layer — by the time we serialize, both
LIST and DETAIL receive the same dict shape.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    raw = getattr(obj, "raw", None)
    if isinstance(raw, dict):
        return raw.get(key, default)
    return getattr(obj, key, default)


@register_serializer(
    tools={
        "unifi_list_content_filters": {"kind": RenderKind.LIST},
        "unifi_get_content_filter_details": {"kind": RenderKind.DETAIL},
    },
)
class ContentFilterSerializer(Serializer):
    primary_key = "id"
    display_columns = ["name", "enabled", "profile"]
    sort_default = "name:asc"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "_id") or _get(obj, "id"),
            "name": _get(obj, "name"),
            "enabled": bool(_get(obj, "enabled", False)),
            "profile": _get(obj, "profile"),
            "applies_to": _get(obj, "applies_to") or _get(obj, "network_ids") or [],
        }


@register_serializer(
    tools={
        "unifi_update_content_filter": {"kind": RenderKind.DETAIL},
        "unifi_delete_content_filter": {"kind": RenderKind.DETAIL},
    },
)
class ContentFilterMutationAckSerializer(Serializer):
    """DETAIL ack for content-filter update + delete (both return ``bool``)."""

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, dict):
            return obj
        raw = getattr(obj, "raw", None)
        if isinstance(raw, dict):
            return raw
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"result": str(obj)}
