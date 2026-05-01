"""Content filter mutation ack serializer.

Phase 6 PR2 Task 22 migrated the read shape (ContentFilter LIST + DETAIL) to
a Strawberry type at ``unifi_api.graphql.types.network.content_filter``.
Only the mutation ack remains here — it covers update + delete (no create
— UniFi ships a fixed set of content-filtering profiles).
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
