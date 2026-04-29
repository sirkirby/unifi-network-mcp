"""Firewall policy/rule serializer."""

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


@register_serializer(
    tools={
        "unifi_list_firewall_policies": {"kind": RenderKind.LIST},
        "unifi_get_firewall_policy_details": {"kind": RenderKind.DETAIL},
    },
    resources=[
        (("network", "firewall/rules"), {"kind": RenderKind.LIST}),
        (("network", "firewall/rules/{id}"), {"kind": RenderKind.DETAIL}),
    ],
)
class FirewallRuleSerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "id"
    display_columns = ["name", "action", "enabled", "predefined"]
    sort_default = "name:asc"

    @staticmethod
    def serialize(obj) -> dict:
        raw = getattr(obj, "raw", obj if isinstance(obj, dict) else {})
        return {
            "id": raw.get("_id") or raw.get("id"),
            "name": raw.get("name"),
            "action": raw.get("action"),
            "enabled": bool(raw.get("enabled", False)),
            "predefined": bool(raw.get("predefined", False)),
            "source": raw.get("source"),
            "destination": raw.get("destination"),
        }
