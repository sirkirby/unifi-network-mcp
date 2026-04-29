"""Protect light serializers (Phase 4A PR2 Cluster 1).

``LightManager.list_lights`` returns plain dicts shaped by
``_format_light_summary``.

PR2 adds ``LightMutationAckSerializer`` for ``protect_update_light``.
The manager's ``update_light`` returns a preview dict
``{light_id, light_name, current_state, proposed_changes}``.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


@register_serializer(
    tools={
        "protect_list_lights": {"kind": RenderKind.LIST},
    },
    resources=[
        (("protect", "lights"), {"kind": RenderKind.LIST}),
    ],
)
class LightSerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "id"
    display_columns = ["name", "model", "state", "is_light_on"]

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "id"),
            "mac": _get(obj, "mac"),
            "name": _get(obj, "name"),
            "model": _get(obj, "model"),
            "state": _get(obj, "state"),
            "is_pir_motion_detected": _get(obj, "is_pir_motion_detected"),
            "is_light_on": _get(obj, "is_light_on"),
        }


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
