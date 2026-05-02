"""Protect chime mutation serializers.

Phase 6 PR3 Task A — the read serializer (``ChimeSerializer``) moved to a
Strawberry type in ``unifi_api.graphql.types.protect.chimes``. The
``protect_list_chimes`` tool is listed in ``PHASE6_TYPE_MIGRATED_TOOLS``
and dispatched via the type_registry by both the REST route and the
action endpoint.

This module now only ships ``ChimeMutationAckSerializer`` for the
trigger/update preview-and-confirm tools, which still flow through the
manager's preview path and produce dict acks.

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
