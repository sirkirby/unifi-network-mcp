"""Access door mutation serializers.

Phase 6 PR4 Task A — the read serializers (``DoorSerializer``,
``DoorGroupSerializer``, ``DoorStatusSerializer``) moved to Strawberry
types in ``unifi_api.graphql.types.access.doors``. The read tools
(``access_list_doors``, ``access_get_door``, ``access_list_door_groups``,
``access_get_door_status``) are listed in ``PHASE6_TYPE_MIGRATED_TOOLS``
and dispatched via the type_registry by both the REST routes and the
action endpoint.

This module now only ships ``DoorMutationAckSerializer`` for the
``access_lock_door`` / ``access_unlock_door`` preview-and-confirm tools,
which still flow through the manager's preview path and produce a dict
ack of the form ``{door_id, current_state, proposed_changes}``.
"""

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


@register_serializer(
    tools={
        "access_lock_door": {"kind": RenderKind.DETAIL},
        "access_unlock_door": {"kind": RenderKind.DETAIL},
    },
)
class DoorMutationAckSerializer(Serializer):
    """DETAIL ack for lock/unlock. Manager preview returns a dict
    (door_id + current_state + proposed_changes); pass through. Bool
    coerces to ``{"success": bool}`` for completeness."""

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
