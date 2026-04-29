"""Access visitor serializers.

``VisitorManager.list_visitors`` / ``get_visitor`` return plain dicts from
the proxy ``visitors`` endpoint (path is best-effort; the manager returns
``[]`` on 404). Field names follow the controller convention; we expose
the catalog-level fields and gracefully fall back to ``None``.

``create_visitor`` / ``delete_visitor`` are preview-pattern mutations —
they return dicts with ``visitor_data`` / ``visitor_id`` and
``proposed_changes``. ``VisitorMutationAckSerializer`` passes those
through unchanged (matches Cluster 1's mutation-ack pattern).
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


@register_serializer(
    tools={
        "access_list_visitors": {"kind": RenderKind.LIST},
        "access_get_visitor": {"kind": RenderKind.DETAIL},
    },
    resources=[
        (("access", "visitors"), {"kind": RenderKind.LIST}),
        (("access", "visitors/{id}"), {"kind": RenderKind.DETAIL}),
    ],
)
class VisitorSerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "id"
    display_columns = ["name", "host_user_id", "valid_from", "valid_until", "status"]
    sort_default = "valid_from:desc"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "id"),
            "name": _get(obj, "name"),
            "host_user_id": _get(obj, "host_user_id"),
            "valid_from": _get(obj, "valid_from") or _get(obj, "access_start"),
            "valid_until": _get(obj, "valid_until") or _get(obj, "access_end"),
            "status": _get(obj, "status"),
            "credential_count": _get(obj, "credential_count"),
        }


@register_serializer(
    tools={
        "access_create_visitor": {"kind": RenderKind.DETAIL},
        "access_delete_visitor": {"kind": RenderKind.DETAIL},
    },
)
class VisitorMutationAckSerializer(Serializer):
    """Pass-through ack for visitor preview/apply dicts."""

    kind = RenderKind.DETAIL

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"result": str(obj)}
