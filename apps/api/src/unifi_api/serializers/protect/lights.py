"""Protect light mutation serializers.

Phase 6 PR3 Task C — the read serializer (``LightSerializer``) moved to a
Strawberry type in ``unifi_api.graphql.types.protect.lights``. The
``protect_list_lights`` tool is listed in ``PHASE6_TYPE_MIGRATED_TOOLS``
and dispatched via the type_registry by both the REST route and the
action endpoint.

This module now only ships ``LightMutationAckSerializer`` for the
``protect_update_light`` preview-and-confirm tool. Confirmed calls return
``{light_id, light_name, applied, errors?}``; failures preserve partial results.
"""

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


@register_serializer(tools={"protect_update_light": {"kind": RenderKind.DETAIL}})
class LightMutationAckSerializer(Serializer):
    """Serialize confirmed light updates, preserving failures and partial results."""

    def serialize_action(self, result, *, tool_name: str, redact_sensitive: bool = True) -> dict:
        envelope = super().serialize_action(result, tool_name=tool_name, redact_sensitive=redact_sensitive)
        if tool_name == "protect_update_light" and isinstance(result, dict) and result.get("errors"):
            envelope["success"] = False
            envelope["error"] = "Failed to update Protect settings: " + "; ".join(result["errors"])
        return envelope

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"result": str(obj)}
