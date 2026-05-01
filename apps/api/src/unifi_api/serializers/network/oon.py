"""OON policy mutation ack serializer.

Phase 6 PR2 Task 22 migrated the read shape (OonPolicy LIST + DETAIL) to a
Strawberry type at ``unifi_api.graphql.types.network.oon``. Only the
mutation ack remains here — it covers create/update/delete/toggle for OON
policies.
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
