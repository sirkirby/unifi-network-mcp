"""Protect recording mutation serializers.

Phase 6 PR3 Task B — read serializers (``RecordingSerializer``,
``RecordingStatusSerializer``) moved to Strawberry types in
``unifi_api.graphql.types.protect.recordings``. Their tools
(``protect_list_recordings``, ``protect_get_recording_status``) are
listed in ``PHASE6_TYPE_MIGRATED_TOOLS`` and dispatched via the
type_registry by both REST routes and the action endpoint.

This module now only ships ``RecordingMutationAckSerializer`` for the
preview-and-confirm tools (``protect_delete_recording``,
``protect_export_clip``), which still flow through the manager's
preview path and produce dict acks.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


@register_serializer(
    tools={
        "protect_delete_recording": {"kind": RenderKind.DETAIL},
        "protect_export_clip": {"kind": RenderKind.DETAIL},
    },
)
class RecordingMutationAckSerializer(Serializer):
    """Pass-through ack for recording mutations. Bool fallback for completeness."""

    @staticmethod
    def serialize(obj: Any) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"result": str(obj)}
