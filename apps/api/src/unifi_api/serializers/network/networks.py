"""Network (LAN/VLAN) serializer.

Phase 4A PR1 Cluster 3 adds the ``NetworkMutationAckSerializer`` for
``unifi_create_network`` and ``unifi_update_network``. Both underlying
``NetworkManager`` methods return either an ``Optional[Dict]`` (create) or
``bool`` (update), so the ack serializer normalises to a DETAIL-shaped
payload.
"""

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


@register_serializer(
    tools={
        "unifi_list_networks": {"kind": RenderKind.LIST},
        "unifi_get_network_details": {"kind": RenderKind.DETAIL},
    },
    resources=[
        (("network", "networks"), {"kind": RenderKind.LIST}),
        (("network", "networks/{id}"), {"kind": RenderKind.DETAIL}),
    ],
)
class NetworkSerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "id"
    display_columns = ["name", "purpose", "vlan", "subnet", "enabled"]
    sort_default = "name:asc"

    @staticmethod
    def serialize(obj) -> dict:
        raw = getattr(obj, "raw", obj if isinstance(obj, dict) else {})
        return {
            "id": raw.get("_id") or raw.get("id"),
            "name": raw.get("name"),
            "purpose": raw.get("purpose"),
            "enabled": bool(raw.get("enabled", False)),
            "vlan": raw.get("vlan"),
            "subnet": raw.get("ip_subnet") or raw.get("subnet"),
        }


@register_serializer(
    tools={
        "unifi_create_network": {"kind": RenderKind.DETAIL},
        "unifi_update_network": {"kind": RenderKind.DETAIL},
    },
)
class NetworkMutationAckSerializer(Serializer):
    """DETAIL ack for network create/update.

    ``create_network`` returns the created dict; ``update_network`` returns
    ``bool``."""

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
