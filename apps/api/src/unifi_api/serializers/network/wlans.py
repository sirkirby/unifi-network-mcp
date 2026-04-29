"""WLAN/SSID serializer.

Phase 4A PR1 Cluster 3 adds the ``WlanMutationAckSerializer`` covering
create / update / delete / toggle on ``NetworkManager``'s WLAN endpoints.
``create_wlan`` returns the created dict; the rest return ``bool``."""

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


@register_serializer(
    tools={
        "unifi_create_wlan": {"kind": RenderKind.DETAIL},
        "unifi_update_wlan": {"kind": RenderKind.DETAIL},
        "unifi_delete_wlan": {"kind": RenderKind.DETAIL},
        "unifi_toggle_wlan": {"kind": RenderKind.DETAIL},
    },
)
class WlanMutationAckSerializer(Serializer):
    """DETAIL ack for WLAN CUD + toggle."""

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
