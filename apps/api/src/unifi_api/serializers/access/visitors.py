"""Access visitor mutation serializers.

Phase 6 PR4 Task B — the read serializer (``VisitorSerializer``) moved
to a Strawberry type in ``unifi_api.graphql.types.access.visitors``. The
``access_list_visitors`` / ``access_get_visitor`` tools are listed in
``PHASE6_TYPE_MIGRATED_TOOLS`` and dispatched via the type_registry by
both the REST routes and the action endpoint.

This module now only ships ``VisitorMutationAckSerializer`` for the
``access_create_visitor`` / ``access_delete_visitor`` preview-and-
confirm tools, which still flow through the manager's preview path and
produce dict acks.
"""

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


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
