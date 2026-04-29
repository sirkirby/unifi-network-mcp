"""Switch + port-related serializers (Phase 4A PR1 Cluster 1).

Manager methods in ``SwitchManager`` largely return either:
  - a list of dicts (port profiles), or
  - a wrapper dict with ``name``, ``model`` and a nested array of rows
    (port_overrides / port_table / lldp_table).

The wrapper-dict shape forces these tools to register as ``DETAIL``
rather than ``LIST`` — the contract checker (``Serializer.serialize_action``)
otherwise rejects a dict for a list-kind tool. The nested rows are
exposed verbatim inside ``data`` so renderers can table them.

Mutation-ack tools (``set_*``, ``configure_*``, ``power_cycle_*``,
``create/update/delete_port_profile``, ``update_switch_stp``) all return
``bool`` from their managers; the ack serializer normalises those into
``{"success": True}`` to satisfy the DETAIL contract per spec
section 5 (EMPTY discipline — prefer DETAIL with a tiny shape).
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
        "unifi_list_port_profiles": {"kind": RenderKind.LIST},
        "unifi_get_port_profile_details": {"kind": RenderKind.DETAIL},
    },
)
class PortProfileSerializer(Serializer):
    primary_key = "id"
    display_columns = ["name", "poe_mode", "native_networkconf_id"]

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "_id") or _get(obj, "id"),
            "name": _get(obj, "name"),
            "native_networkconf_id": _get(obj, "native_networkconf_id"),
            "tagged_networkconf_ids": _get(obj, "tagged_networkconf_ids", []) or [],
            "poe_mode": _get(obj, "poe_mode"),
            "isolation": _get(obj, "isolation"),
        }


@register_serializer(tools={"unifi_get_switch_ports": {"kind": RenderKind.DETAIL}})
class SwitchPortsSerializer(Serializer):
    """Wrapper around ``SwitchManager.get_switch_ports`` — manager returns a
    dict ``{name, model, port_overrides: [...]}``, which is DETAIL-shaped."""

    @staticmethod
    def serialize(obj) -> dict:
        port_overrides = _get(obj, "port_overrides", []) or []
        normalised = [
            {
                "port_idx": _get(p, "port_idx"),
                "name": _get(p, "name"),
                "portconf_id": _get(p, "portconf_id"),
                "poe_mode": _get(p, "poe_mode"),
                "op_mode": _get(p, "op_mode"),
            }
            for p in port_overrides
        ]
        return {
            "name": _get(obj, "name"),
            "model": _get(obj, "model"),
            "port_overrides": normalised,
        }


@register_serializer(tools={"unifi_get_port_stats": {"kind": RenderKind.DETAIL}})
class PortStatsSerializer(Serializer):
    """Manager returns ``{name, model, port_table: [...]}``."""

    @staticmethod
    def serialize(obj) -> dict:
        port_table = _get(obj, "port_table", []) or []
        normalised = [
            {
                "port_idx": _get(p, "port_idx"),
                "name": _get(p, "name"),
                "enable": bool(_get(p, "enable", True)),
                "speed": _get(p, "speed"),
                "duplex": _get(p, "full_duplex"),
                "tx_bytes": _get(p, "tx_bytes", 0),
                "rx_bytes": _get(p, "rx_bytes", 0),
                "tx_packets": _get(p, "tx_packets", 0),
                "rx_packets": _get(p, "rx_packets", 0),
                "tx_dropped": _get(p, "tx_dropped", 0),
                "rx_dropped": _get(p, "rx_dropped", 0),
                "poe_enable": bool(_get(p, "poe_enable", False)),
                "poe_mode": _get(p, "poe_mode"),
                "poe_power": _get(p, "poe_power"),
            }
            for p in port_table
        ]
        return {
            "name": _get(obj, "name"),
            "model": _get(obj, "model"),
            "port_table": normalised,
        }


@register_serializer(tools={"unifi_get_switch_capabilities": {"kind": RenderKind.DETAIL}})
class SwitchCapabilitiesSerializer(Serializer):
    @staticmethod
    def serialize(obj) -> dict:
        caps = _get(obj, "switch_caps", {}) or {}
        return {
            "name": _get(obj, "name"),
            "model": _get(obj, "model"),
            "switch_caps": caps,
            "stp_version": _get(obj, "stp_version"),
            "stp_priority": _get(obj, "stp_priority"),
            "jumboframe_enabled": _get(obj, "jumboframe_enabled"),
            "dot1x_portctrl_enabled": _get(obj, "dot1x_portctrl_enabled"),
        }


# Mutation acks — DETAIL with tiny shape (spec section 5 EMPTY discipline).
# Manager methods here return bool/dict; we normalise to a small DETAIL payload.
@register_serializer(
    tools={
        "unifi_create_port_profile": {"kind": RenderKind.DETAIL},
        "unifi_update_port_profile": {"kind": RenderKind.DETAIL},
        "unifi_delete_port_profile": {"kind": RenderKind.DETAIL},
        "unifi_set_switch_port_profile": {"kind": RenderKind.DETAIL},
        "unifi_configure_port_aggregation": {"kind": RenderKind.DETAIL},
        "unifi_configure_port_mirror": {"kind": RenderKind.DETAIL},
        "unifi_power_cycle_port": {"kind": RenderKind.DETAIL},
        "unifi_set_jumbo_frames": {"kind": RenderKind.DETAIL},
        "unifi_update_switch_stp": {"kind": RenderKind.DETAIL},
    },
)
class SwitchMutationAckSerializer(Serializer):
    """Generic ack for switch-side mutations. Most managers return ``bool``
    — coerce to ``{"success": bool}``. Dict responses (e.g. ``create_port_profile``
    returns the created profile) pass through with minimal coercion."""

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
