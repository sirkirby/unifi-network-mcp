"""Out-of-network (OON) policy serializers (Phase 4A PR1 Cluster 4).

``OonManager`` exposes ``get_oon_policies()`` / ``get_oon_policy_by_id()``
/ ``create_oon_policy()`` / ``update_oon_policy()`` /
``toggle_oon_policy()`` / ``delete_oon_policy()`` on V2 OON endpoints.
Mutations return ``bool`` (or ``Optional[bool]`` for toggle) and
``create_*`` returns the created dict.

OON policies bundle ``targets`` (a list of ``{type, value}`` matchers
covering MACs, group IDs, etc.) plus a ``secure`` config (with nested
``internet`` mode), a ``qos`` slice, and a ``route`` slice. For the LIST
render we only need name/enabled and the target list (re-exposed as
``applies_to``); the registry preserves everything else through normal
serialization.

``restriction_level`` is a controller-side label that the manager passes
through unchanged when present — newer firmware exposes it; older
firmware leaves it out.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    raw = getattr(obj, "raw", None)
    if isinstance(raw, dict):
        return raw.get(key, default)
    return getattr(obj, key, default)


@register_serializer(
    tools={
        "unifi_list_oon_policies": {"kind": RenderKind.LIST},
        "unifi_get_oon_policy_details": {"kind": RenderKind.DETAIL},
    },
)
class OonPolicySerializer(Serializer):
    primary_key = "id"
    display_columns = ["name", "enabled", "restriction_level"]
    sort_default = "name:asc"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "_id") or _get(obj, "id"),
            "name": _get(obj, "name"),
            "enabled": bool(_get(obj, "enabled", False)),
            "applies_to": _get(obj, "targets") or _get(obj, "applies_to") or [],
            "restriction_level": _get(obj, "restriction_level"),
        }


@register_serializer(
    tools={
        "unifi_create_oon_policy": {"kind": RenderKind.DETAIL},
        "unifi_update_oon_policy": {"kind": RenderKind.DETAIL},
        "unifi_delete_oon_policy": {"kind": RenderKind.DETAIL},
        "unifi_toggle_oon_policy": {"kind": RenderKind.DETAIL},
    },
)
class OonMutationAckSerializer(Serializer):
    """DETAIL ack for OON policy mutations.

    ``create_oon_policy`` returns the created dict; ``update_*`` and
    ``delete_*`` return ``bool``; ``toggle_oon_policy`` returns
    ``Optional[bool]``."""

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if obj is None:
            return {"success": False}
        if isinstance(obj, dict):
            return obj
        raw = getattr(obj, "raw", None)
        if isinstance(raw, dict):
            return raw
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"result": str(obj)}
