"""Protect light mutation serializers.

Phase 6 PR3 Task C — the read serializer (``LightSerializer``) moved to a
Strawberry type in ``unifi_api.graphql.types.protect.lights``. The
``protect_list_lights`` tool is listed in ``PHASE6_TYPE_MIGRATED_TOOLS``
and dispatched via the type_registry by both the REST route and the
action endpoint.

This module now only ships ``LightMutationAckSerializer`` for the
``protect_update_light`` preview-and-confirm tool, which still flows
through the manager's preview path and produces a dict ack of the form
``{light_id, light_name, current_state, proposed_changes}``.
"""

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


@register_serializer(tools={"protect_update_light": {"kind": RenderKind.DETAIL}})
class LightMutationAckSerializer(Serializer):
    """``LightManager.update_light`` returns the preview dict; pass through.
    Bool fallback for completeness."""

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"result": str(obj)}
