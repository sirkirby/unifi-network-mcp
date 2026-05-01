"""Static DNS record serializers (Phase 4A PR1 Cluster 3).

Phase 6 PR2 Task 21 migrated the read shape (list/detail) to a Strawberry
type at ``unifi_api.graphql.types.network.dns.DnsRecord``. Only the
mutation ack remains here.
"""

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


@register_serializer(
    tools={
        "unifi_create_dns_record": {"kind": RenderKind.DETAIL},
        "unifi_update_dns_record": {"kind": RenderKind.DETAIL},
        "unifi_delete_dns_record": {"kind": RenderKind.DETAIL},
    },
)
class DnsMutationAckSerializer(Serializer):
    """DETAIL ack for DNS-record CUD operations.

    ``create_dns_record`` returns the created dict; ``update_*`` /
    ``delete_*`` return ``bool``. Coerce both to a DETAIL-shaped payload."""

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
