"""Static + active + traffic route serializers (Phase 4A PR1 Cluster 3).

Phase 6 PR2 Task 21 migrated the read shapes (static routes, active routes,
traffic routes) to Strawberry types at
``unifi_api.graphql.types.network.route``. Only the cross-cutting mutation
ack remains here.
"""

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


@register_serializer(
    tools={
        "unifi_create_route": {"kind": RenderKind.DETAIL},
        "unifi_update_route": {"kind": RenderKind.DETAIL},
        "unifi_update_traffic_route": {"kind": RenderKind.DETAIL},
        "unifi_toggle_traffic_route": {"kind": RenderKind.DETAIL},
    },
)
class RouteMutationAckSerializer(Serializer):
    """DETAIL ack for static + traffic route mutations.

    ``create_route`` returns the created dict; the rest return ``bool``."""

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
