"""QoS rule mutation ack serializer.

Phase 6 PR2 Task 22 migrated the read shape (QoS rule LIST + DETAIL) to a
Strawberry type at ``unifi_api.graphql.types.network.qos``. Only the
mutation ack remains here — it covers create/update/toggle for QoS rules.
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
        "unifi_create_qos_rule": {"kind": RenderKind.DETAIL},
        "unifi_create_simple_qos_rule": {"kind": RenderKind.DETAIL},
        "unifi_update_qos_rule": {"kind": RenderKind.DETAIL},
        "unifi_toggle_qos_rule_enabled": {"kind": RenderKind.DETAIL},
    },
)
class QosMutationAckSerializer(Serializer):
    """DETAIL ack for QoS rule mutations.

    ``create_*`` returns the created dict; ``update_*`` and toggle
    return ``bool``."""

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, dict):
            return obj
        raw = getattr(obj, "raw", None)
        if isinstance(raw, dict):
            return raw
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"result": str(obj)}
