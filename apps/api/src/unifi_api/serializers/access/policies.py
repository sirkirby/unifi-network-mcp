"""Access policy mutation serializer.

Phase 6 PR4 Task B — the read serializer (``PolicySerializer``) moved to
a Strawberry type in ``unifi_api.graphql.types.access.policies``. The
``access_list_policies`` / ``access_get_policy`` tools are listed in
``PHASE6_TYPE_MIGRATED_TOOLS`` and dispatched via the type_registry by
both the REST routes and the action endpoint.

This module now only ships ``PolicyMutationAckSerializer`` for
``access_update_policy`` — that tool dispatches via the manager's preview
path and returns a dict ack (current_state + proposed_changes on preview;
``{"result": "success", ...}`` on apply).
"""

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


@register_serializer(
    tools={
        "access_update_policy": {"kind": RenderKind.DETAIL},
    },
)
class PolicyMutationAckSerializer(Serializer):
    """DETAIL ack for ``access_update_policy``. Preview/apply both return
    dicts; pass through. Bool coerces to ``{"success": bool}``."""

    kind = RenderKind.DETAIL

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, dict):
            return obj
        if obj is None:
            return {"success": False}
        return {"result": str(obj)}
