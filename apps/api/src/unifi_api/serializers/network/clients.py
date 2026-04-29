"""Network client serializer."""

from datetime import datetime, timezone

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _iso(ts: int | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


@register_serializer(
    tools={
        "unifi_list_clients": {"kind": RenderKind.LIST},
        "unifi_get_client_details": {"kind": RenderKind.DETAIL},
    },
    resources=[
        (("network", "clients"), {"kind": RenderKind.LIST}),
        (("network", "clients/{mac}"), {"kind": RenderKind.DETAIL}),
    ],
)
class ClientSerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "mac"
    display_columns = ["hostname", "ip", "status", "last_seen"]
    sort_default = "last_seen:desc"

    @staticmethod
    def serialize(obj) -> dict:
        raw = getattr(obj, "raw", obj if isinstance(obj, dict) else {})
        return {
            "mac": raw.get("mac"),
            "ip": raw.get("last_ip") or raw.get("ip"),
            "hostname": raw.get("hostname") or raw.get("name"),
            "is_wired": bool(raw.get("is_wired", False)),
            "is_guest": bool(raw.get("is_guest", False)),
            "status": "online" if raw.get("is_online") else "offline",
            "last_seen": _iso(raw.get("last_seen")),
            "first_seen": _iso(raw.get("first_seen")),
            "note": raw.get("note") or None,
            "usergroup_id": raw.get("usergroup_id") or None,
        }
