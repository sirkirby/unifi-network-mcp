"""Protect liveview mutation serializers.

Phase 6 PR3 Task C — the read serializer (``LiveviewSerializer``) moved
to a Strawberry type in ``unifi_api.graphql.types.protect.liveviews``.
The ``protect_list_liveviews`` tool is listed in
``PHASE6_TYPE_MIGRATED_TOOLS`` and dispatched via the type_registry by
both the REST route and the action endpoint.

This module now only ships ``LiveviewMutationAckSerializer`` for the
``protect_create_liveview`` / ``protect_delete_liveview``
preview-and-confirm tools. Both manager methods today return
``supported=False`` preview dicts since uiprotect does not expose direct
create/delete APIs, but the serializer pass-through is kept for forward
compatibility.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


@register_serializer(
    tools={
        "protect_create_liveview": {"kind": RenderKind.DETAIL},
        "protect_delete_liveview": {"kind": RenderKind.DETAIL},
    },
)
class LiveviewMutationAckSerializer(Serializer):
    """Pass-through for liveview create/delete preview dicts. Bool fallback."""

    @staticmethod
    def serialize(obj: Any) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"result": str(obj)}
