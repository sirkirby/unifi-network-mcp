"""AP group mutation ack serializer (Phase 4A PR1 Cluster 3).

Phase 6 PR2 Task 24 — read shape (ApGroupSerializer) migrated to a Strawberry
type in ``unifi_api.graphql.types.network.ap_group``. Only the mutation ack
remains here so create/update/delete continue to dispatch through the
serializer registry.

AP groups live on V2 ``/apgroups`` and ride on ``NetworkManager`` (not a
dedicated manager). The mutation ack normalises the manager's mixed return
shapes (``Optional[Dict]`` for create, ``bool`` for update/delete) to a
DETAIL-shaped payload per spec section 5 (EMPTY discipline).
"""

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


@register_serializer(
    tools={
        "unifi_create_ap_group": {"kind": RenderKind.DETAIL},
        "unifi_update_ap_group": {"kind": RenderKind.DETAIL},
        "unifi_delete_ap_group": {"kind": RenderKind.DETAIL},
    },
)
class ApGroupMutationAckSerializer(Serializer):
    """DETAIL ack for AP group CUD operations.

    ``create_ap_group`` returns the created dict; ``update_*``/``delete_*``
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
