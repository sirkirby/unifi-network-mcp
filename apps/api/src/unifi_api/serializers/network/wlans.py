"""WLAN/SSID serializer."""

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


@register_serializer(
    tools={
        "unifi_list_wlans": {"kind": RenderKind.LIST},
        "unifi_get_wlan_details": {"kind": RenderKind.DETAIL},
    },
    resources=[
        (("network", "wlans"), {"kind": RenderKind.LIST}),
        (("network", "wlans/{id}"), {"kind": RenderKind.DETAIL}),
    ],
)
class WlanSerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "id"
    display_columns = ["name", "security", "enabled", "vlan_id"]
    sort_default = "name:asc"

    @staticmethod
    def serialize(obj) -> dict:
        raw = getattr(obj, "raw", obj if isinstance(obj, dict) else {})
        return {
            "id": raw.get("_id") or raw.get("id"),
            "name": raw.get("name"),
            "enabled": bool(raw.get("enabled", False)),
            "security": raw.get("security"),
            "network_id": raw.get("networkconf_id") or raw.get("network_id"),
            "hide_ssid": bool(raw.get("hide_ssid", False)),
            "vlan_id": raw.get("vlan") or raw.get("vlan_id"),
        }
