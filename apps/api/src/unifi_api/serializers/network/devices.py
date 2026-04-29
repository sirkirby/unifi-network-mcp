"""Network device serializer + Phase 4A PR1 Cluster 1 extensions.

The base ``DeviceSerializer`` covers ``unifi_list_devices`` /
``unifi_get_device_details``. The remaining device-side tools in the
"devices & switches" cluster are covered here:

  - ``DeviceRadioSerializer`` (DETAIL) — ``unifi_get_device_radio``;
    manager returns ``{mac, name, model, radios: [...]}``.
  - ``LldpNeighborSerializer`` (DETAIL) — ``unifi_get_lldp_neighbors``;
    manager returns wrapper dict ``{name, model, lldp_table: [...]}``,
    so DETAIL (matches the SwitchPortsSerializer pattern).
  - ``RogueApSerializer`` (LIST) — both ``unifi_list_rogue_aps`` and
    ``unifi_list_known_rogue_aps``; the second sets ``is_known=True``.
  - ``RfScanResultSerializer`` (LIST) — ``unifi_get_rf_scan_results``.
  - ``AvailableChannelSerializer`` (LIST) — ``unifi_list_available_channels``.
  - ``SpeedtestStatusSerializer`` (DETAIL) — ``unifi_get_speedtest_status``.
  - ``DeviceMutationAckSerializer`` (DETAIL passthrough) — covers all
    bool-returning mutation tools per spec section 5 EMPTY discipline.
"""

from typing import Any

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


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    raw = getattr(obj, "raw", None)
    if isinstance(raw, dict):
        return raw.get(key, default)
    return getattr(obj, key, default)


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


@register_serializer(tools={"unifi_get_device_radio": {"kind": RenderKind.DETAIL}})
class DeviceRadioSerializer(Serializer):
    """Manager returns ``{mac, name, model, radios: [...]}`` (or None for
    non-AP devices). Pass through with light field whitelisting on the
    radio entries."""

    @staticmethod
    def serialize(obj) -> dict:
        radios = _get(obj, "radios", []) or []
        return {
            "mac": _get(obj, "mac"),
            "name": _get(obj, "name"),
            "model": _get(obj, "model"),
            "radios": [
                {
                    "name": _get(r, "name"),
                    "radio": _get(r, "radio"),
                    "channel": _get(r, "channel"),
                    "ht": _get(r, "ht"),
                    "tx_power": _get(r, "tx_power"),
                    "tx_power_mode": _get(r, "tx_power_mode"),
                    "current_channel": _get(r, "current_channel"),
                    "current_tx_power": _get(r, "current_tx_power"),
                    "num_sta": _get(r, "num_sta"),
                }
                for r in radios
            ],
        }


@register_serializer(tools={"unifi_get_lldp_neighbors": {"kind": RenderKind.DETAIL}})
class LldpNeighborSerializer(Serializer):
    """Manager returns ``{name, model, lldp_table: [...]}``. The lldp_table
    rows are passed through with field whitelisting."""

    @staticmethod
    def serialize(obj) -> dict:
        rows = _get(obj, "lldp_table", []) or []
        return {
            "name": _get(obj, "name"),
            "model": _get(obj, "model"),
            "lldp_table": [
                {
                    "local_port_idx": _get(r, "local_port_idx"),
                    "chassis_id": _get(r, "chassis_id"),
                    "port_id": _get(r, "port_id"),
                    "system_name": _get(r, "system_name"),
                    "capabilities": _get(r, "capabilities", []) or [],
                }
                for r in rows
            ],
        }


@register_serializer(
    tools={
        "unifi_list_rogue_aps": {"kind": RenderKind.LIST},
        "unifi_list_known_rogue_aps": {"kind": RenderKind.LIST},
    },
)
class RogueApSerializer(Serializer):
    """Both endpoints return list[dict]. ``is_known`` is derived from the
    tool name at the registry layer — it cannot be inferred from the row
    alone, so we look at a hint key set by ``serialize_action``. We
    override ``serialize_action`` to thread ``tool_name`` into ``serialize``
    for this single class."""

    primary_key = "bssid"
    display_columns = ["bssid", "ssid", "channel", "signal_dbm", "last_seen"]

    @staticmethod
    def _row(obj, *, is_known: bool) -> dict:
        return {
            "bssid": _get(obj, "bssid"),
            "ssid": _get(obj, "essid") or _get(obj, "ssid"),
            "channel": _get(obj, "channel"),
            "signal_dbm": _get(obj, "rssi") or _get(obj, "signal"),
            "last_seen": _get(obj, "last_seen"),
            "is_known": is_known,
        }

    @staticmethod
    def serialize(obj) -> dict:
        # Default path (callers that bypass serialize_action) — assume unknown.
        return RogueApSerializer._row(obj, is_known=False)

    def serialize_action(self, result, *, tool_name: str) -> dict:
        kind = self._kind_for_tool(tool_name)
        hint = self._render_hint(kind)
        is_known = tool_name == "unifi_list_known_rogue_aps"
        if not isinstance(result, list):
            from unifi_api.serializers._base import SerializerContractError

            raise SerializerContractError(
                f"tool '{tool_name}' declared kind=list but manager returned "
                f"{type(result).__name__}"
            )
        return {
            "success": True,
            "data": [RogueApSerializer._row(item, is_known=is_known) for item in result],
            "render_hint": hint,
        }


@register_serializer(tools={"unifi_get_rf_scan_results": {"kind": RenderKind.LIST}})
class RfScanResultSerializer(Serializer):
    primary_key = "bssid"
    display_columns = ["bssid", "ssid", "channel", "signal_dbm"]

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "bssid": _get(obj, "bssid"),
            "ssid": _get(obj, "essid") or _get(obj, "ssid"),
            "channel": _get(obj, "channel"),
            "signal_dbm": _get(obj, "rssi") or _get(obj, "signal"),
            "captured_at": _get(obj, "ts") or _get(obj, "captured_at"),
        }


@register_serializer(tools={"unifi_list_available_channels": {"kind": RenderKind.LIST}})
class AvailableChannelSerializer(Serializer):
    primary_key = "channel"
    display_columns = ["channel", "frequency_mhz", "width_mhz", "allowed"]

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "channel": _get(obj, "channel"),
            "frequency_mhz": _get(obj, "freq") or _get(obj, "frequency_mhz"),
            "width_mhz": _get(obj, "ht") or _get(obj, "width_mhz"),
            "allowed": bool(_get(obj, "allowed", True)),
        }


@register_serializer(tools={"unifi_get_speedtest_status": {"kind": RenderKind.DETAIL}})
class SpeedtestStatusSerializer(Serializer):
    @staticmethod
    def serialize(obj) -> dict:
        # Controller exposes status_download/status_upload as Mbps and
        # latency in ms; status int (0=idle, 1=running) is mapped to a label.
        status_raw = _get(obj, "status")
        if isinstance(status_raw, int):
            status_label = "running" if status_raw == 1 else "idle"
        elif isinstance(status_raw, str):
            status_label = status_raw
        else:
            status_label = None
        return {
            "status": status_label,
            "download_mbps": _get(obj, "status_download") or _get(obj, "download_mbps"),
            "upload_mbps": _get(obj, "status_upload") or _get(obj, "upload_mbps"),
            "latency_ms": _get(obj, "latency") or _get(obj, "latency_ms"),
            "last_run": _get(obj, "rundate") or _get(obj, "last_run"),
        }


@register_serializer(
    tools={
        "unifi_adopt_device": {"kind": RenderKind.DETAIL},
        "unifi_force_provision_device": {"kind": RenderKind.DETAIL},
        "unifi_locate_device": {"kind": RenderKind.DETAIL},
        "unifi_reboot_device": {"kind": RenderKind.DETAIL},
        "unifi_rename_device": {"kind": RenderKind.DETAIL},
        "unifi_set_device_led": {"kind": RenderKind.DETAIL},
        "unifi_set_site_leds": {"kind": RenderKind.DETAIL},
        "unifi_toggle_device": {"kind": RenderKind.DETAIL},
        "unifi_trigger_rf_scan": {"kind": RenderKind.DETAIL},
        "unifi_trigger_speedtest": {"kind": RenderKind.DETAIL},
        "unifi_update_device_radio": {"kind": RenderKind.DETAIL},
        "unifi_upgrade_device": {"kind": RenderKind.DETAIL},
    },
)
class DeviceMutationAckSerializer(Serializer):
    """Generic ack for device-side mutations. All managers here return
    ``bool``; coerce to ``{"success": bool}`` to satisfy the DETAIL contract."""

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
