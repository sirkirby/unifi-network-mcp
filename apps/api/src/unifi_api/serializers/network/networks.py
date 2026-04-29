"""Network (LAN/VLAN) serializer."""

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
