"""Network device serializer."""

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


_STATE_MAP = {
    0: "disconnected",
    1: "connected",
    2: "pending",
    4: "upgrading",
    5: "provisioning",
    6: "heartbeat-missed",
    7: "adopting",
    9: "adoption-error",
    11: "isolated",
}


@register_serializer(
    tools={
        "unifi_list_devices": {"kind": RenderKind.LIST},
        "unifi_get_device_details": {"kind": RenderKind.DETAIL},
    },
    resources=[
        (("network", "devices"), {"kind": RenderKind.LIST}),
        (("network", "devices/{mac}"), {"kind": RenderKind.DETAIL}),
    ],
)
class DeviceSerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "mac"
    display_columns = ["name", "model", "type", "state", "ip"]
    sort_default = "name:asc"

    @staticmethod
    def serialize(obj) -> dict:
        raw = getattr(obj, "raw", obj if isinstance(obj, dict) else {})
        state_raw = raw.get("state")
        return {
            "mac": raw.get("mac"),
            "name": raw.get("name"),
            "model": raw.get("model"),
            "type": raw.get("type"),
            "version": raw.get("version"),
            "uptime": raw.get("uptime"),
            "state": _STATE_MAP.get(state_raw, state_raw),
            "ip": raw.get("ip"),
            "ports": raw.get("port_table") or raw.get("ports"),
        }
