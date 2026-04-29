"""Firewall policy/rule, group, and zone serializers.

The original ``FirewallRuleSerializer`` (Phase 3) covers
``unifi_list_firewall_policies`` / ``unifi_get_firewall_policy_details``
from ``firewall_manager.get_firewall_policies``.

Phase 4A PR1 Cluster 4 extends this module with:

* ``FirewallGroupSerializer`` — V1 ``/rest/firewallgroup``. Members live
  under ``group_members`` (re-exposed as ``members``); ``group_type``
  is one of ``address-group`` / ``ipv6-address-group`` / ``port-group``.
* ``FirewallZoneSerializer`` — V2 ``/firewall/zone-matrix`` (with a
  fallback to ``/firewall/zones``). The matrix payload is dropped at the
  manager layer so we only see zone metadata here.
* ``FirewallMutationAckSerializer`` — DETAIL ack for all firewall-policy
  and firewall-group CUD/toggle mutations. ``create_*`` may return a
  dict (or ``FirewallPolicy``); ``update_*`` / ``delete_*`` /
  ``toggle_*`` return ``bool``.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    raw = getattr(obj, "raw", None)
    if isinstance(raw, dict):
        return raw.get(key, default)
    return getattr(obj, key, default)


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


@register_serializer(
    tools={
        "unifi_list_firewall_groups": {"kind": RenderKind.LIST},
        "unifi_get_firewall_group_details": {"kind": RenderKind.DETAIL},
    },
)
class FirewallGroupSerializer(Serializer):
    primary_key = "id"
    display_columns = ["name", "group_type", "members"]
    sort_default = "name:asc"

    @staticmethod
    def serialize(obj) -> dict:
        members = _get(obj, "group_members") or _get(obj, "members") or []
        return {
            "id": _get(obj, "_id") or _get(obj, "id"),
            "name": _get(obj, "name"),
            "group_type": _get(obj, "group_type"),
            "members": members,
        }


@register_serializer(
    tools={
        "unifi_list_firewall_zones": {"kind": RenderKind.LIST},
    },
)
class FirewallZoneSerializer(Serializer):
    primary_key = "id"
    display_columns = ["name", "default_policy", "networks"]
    sort_default = "name:asc"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "_id") or _get(obj, "id"),
            "name": _get(obj, "name"),
            "networks": _get(obj, "networks") or _get(obj, "network_ids") or [],
            "default_policy": _get(obj, "default_policy")
            or _get(obj, "default_action"),
        }


@register_serializer(
    tools={
        "unifi_create_firewall_policy": {"kind": RenderKind.DETAIL},
        "unifi_create_simple_firewall_policy": {"kind": RenderKind.DETAIL},
        "unifi_update_firewall_policy": {"kind": RenderKind.DETAIL},
        "unifi_delete_firewall_policy": {"kind": RenderKind.DETAIL},
        "unifi_toggle_firewall_policy": {"kind": RenderKind.DETAIL},
        "unifi_create_firewall_group": {"kind": RenderKind.DETAIL},
        "unifi_update_firewall_group": {"kind": RenderKind.DETAIL},
        "unifi_delete_firewall_group": {"kind": RenderKind.DETAIL},
    },
)
class FirewallMutationAckSerializer(Serializer):
    """DETAIL ack for firewall policy + group mutations.

    ``create_*`` returns a dict or ``FirewallPolicy``; ``update_*`` /
    ``delete_*`` / ``toggle_*`` return ``bool``."""

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
