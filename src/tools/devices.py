"""
Unifi Network MCP device management tools.

This module provides MCP tools to manage devices in a Unifi Network Controller.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

# Import the global FastMCP server instance, config, and managers
from src.runtime import config, device_manager, server
from src.utils.confirmation import create_preview, preview_response, should_auto_confirm, update_preview
from src.utils.permissions import parse_permission

logger = logging.getLogger(__name__)


def get_wifi_bands(device: Dict[str, Any]) -> List[str]:
    """Extract active WiFi bands from device radio table."""
    bands = set()
    for radio in device.get("radio_table", []):
        if radio.get("radio") == "na":
            bands.add("5GHz")
        elif radio.get("radio") == "ng":
            bands.add("2.4GHz")
        elif radio.get("radio") == "wifi6e":
            bands.add("6GHz")
    return sorted(list(bands))


@server.tool(
    name="unifi_list_devices",
    description="List devices adopted by the Unifi Network controller for the current site",
)
async def list_devices(device_type: str = "all", status: str = "all", include_details: bool = False) -> Dict[str, Any]:
    """Implementation for listing devices."""
    try:
        devices = await device_manager.get_devices()

        # Convert Device objects to plain dictionaries for easier filtering
        devices_raw = [d.raw if hasattr(d, "raw") else d for d in devices]

        # Filter by device type
        if device_type != "all":
            prefix_map = {
                "ap": "uap",
                "switch": ("usw", "usk"),
                "gateway": ("ugw", "udm", "uxg"),
                "pdu": "usp",
            }
            prefixes = prefix_map.get(device_type)
            if prefixes:
                devices_raw = [d for d in devices_raw if d.get("type", "").startswith(prefixes)]

        # Filter by status
        if status != "all":
            status_map = {
                "online": 1,
                "offline": 0,
                "pending": 2,
                "adopting": 4,
                "provisioning": 5,
                "upgrading": 6,
            }
            target_state = status_map.get(status)
            if target_state is not None:
                devices_raw = [d for d in devices_raw if d.get("state") == target_state]
            else:
                logger.warning(f"Unknown status filter: {status}")

        formatted_devices = []
        state_map = {
            0: "offline",
            1: "online",
            2: "pending_adoption",
            4: "managed_by_other/adopting",
            5: "provisioning",
            6: "upgrading",
            11: "error/heartbeat_missed",
        }

        for device in devices_raw:
            device_state = device.get("state", 0)
            device_status_str = state_map.get(device_state, f"unknown_state ({device_state})")

            device_info = {
                "mac": device.get("mac", ""),
                "name": device.get("name", device.get("model", "Unknown")),
                "model": device.get("model", ""),
                "type": device.get("type", ""),
                "ip": device.get("ip", ""),
                "status": device_status_str,
                "uptime": str(timedelta(seconds=device.get("uptime", 0))) if device.get("uptime") else "N/A",
                "last_seen": (
                    datetime.fromtimestamp(device.get("last_seen", 0)).isoformat() if device.get("last_seen") else "N/A"
                ),
                "firmware": device.get("version", ""),
                "adopted": device.get("adopted", False),
                "_id": device.get("_id", ""),
            }

            if include_details:
                details_to_add = {
                    "serial": device.get("serial", ""),
                    "hw_revision": device.get("hw_rev", ""),
                    "model_display": device.get("model_display", device.get("model")),
                    "clients": device.get("num_sta", 0),
                }

                device_type_prefix = device.get("type", "")[:3]

                if device_type_prefix == "uap":
                    details_to_add.update(
                        {
                            "radio_table": device.get("radio_table", []),
                            "vap_table": device.get("vap_table", []),
                            "wifi_bands": get_wifi_bands(device),
                            "experience_score": device.get("satisfaction", 0),
                            "num_clients": device.get("num_sta", 0),
                        }
                    )
                elif device_type_prefix in ["usw", "usk"]:
                    details_to_add.update(
                        {
                            "ports": device.get("port_table", []),
                            "total_ports": len(device.get("port_table", [])),
                            "num_clients": device.get("user-num_sta", 0) + device.get("guest-num_sta", 0),
                            "poe_info": {
                                "poe_current": device.get("poe_current"),
                                "poe_power": device.get("poe_power"),
                                "poe_voltage": device.get("poe_voltage"),
                            },
                        }
                    )
                elif device_type_prefix in ["ugw", "udm", "uxg"]:
                    details_to_add.update(
                        {
                            "wan1": device.get("wan1", {}),
                            "wan2": device.get("wan2", {}),
                            "num_clients": device.get("user-num_sta", 0) + device.get("guest-num_sta", 0),
                            "network_table": device.get("network_table", []),
                            "system_stats": device.get("system-stats", {}),
                            "speedtest_status": device.get("speedtest-status", {}),
                        }
                    )

                device_info.update(details_to_add)

            formatted_devices.append(device_info)

        return {
            "success": True,
            "site": device_manager._connection.site,
            "filter_type": device_type,
            "filter_status": status,
            "count": len(formatted_devices),
            "devices": formatted_devices,
        }
    except Exception as e:
        logger.error(f"Error listing devices: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_get_device_details",
    description="Get detailed information about a specific device by MAC address",
)
async def get_device_details(mac_address: str) -> Dict[str, Any]:
    """Implementation for getting device details."""
    try:
        device = await device_manager.get_device_details(mac_address)
        if device:
            return {
                "success": True,
                "site": device_manager._connection.site,
                "device": device.raw if hasattr(device, "raw") else device,
            }
        return {
            "success": False,
            "error": f"Device not found with MAC address: {mac_address}",
        }
    except Exception as e:
        logger.error(f"Error getting device details for {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_reboot_device",
    description="Reboot a specific device by MAC address",
    permission_category="devices",
    permission_action="update",
)
async def reboot_device(mac_address: str, confirm: bool = False) -> Dict[str, Any]:
    """Implementation for rebooting a device."""
    if not parse_permission(config.permissions, "device", "reboot"):
        logger.warning(f"Permission denied for rebooting device ({mac_address}).")
        return {"success": False, "error": "Permission denied to reboot device."}

    try:
        # Fetch device details to provide context in the preview
        device = await device_manager.get_device_details(mac_address)
        if not device:
            return {
                "success": False,
                "error": f"Device not found with MAC address: {mac_address}",
            }

        # Extract device info for preview
        device_raw = device.raw if hasattr(device, "raw") else device
        device_name = device_raw.get("name", device_raw.get("model", "Unknown"))
        device_state = device_raw.get("state", 0)
        device_model = device_raw.get("model", "")

        state_map = {
            0: "offline",
            1: "online",
            2: "pending_adoption",
            4: "managed_by_other/adopting",
            5: "provisioning",
            6: "upgrading",
            11: "error/heartbeat_missed",
        }
        device_status = state_map.get(device_state, f"unknown_state ({device_state})")

        if not confirm and not should_auto_confirm():
            return preview_response(
                action="reboot",
                resource_type="device",
                resource_id=mac_address,
                resource_name=device_name,
                current_state={
                    "status": device_status,
                    "model": device_model,
                    "ip": device_raw.get("ip", ""),
                },
                proposed_changes={"action": "reboot - device will restart"},
                warnings=["Device will be offline for 1-2 minutes during reboot"],
            )

        logger.info(f"Attempting to reboot device: {mac_address}")
        success = await device_manager.reboot_device(mac_address)

        if success:
            return {
                "success": True,
                "message": f"Reboot initiated for device: {mac_address}",
            }
        else:
            return {
                "success": False,
                "error": f"Failed to reboot device: {mac_address}",
            }
    except Exception as e:
        logger.error(f"Error rebooting device {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_rename_device",
    description="Rename a device in the Unifi Network controller by MAC address",
    permission_category="devices",
    permission_action="update",
)
async def rename_device(mac_address: str, name: str, confirm: bool = False) -> Dict[str, Any]:
    """Implementation for renaming a device."""
    if not parse_permission(config.permissions, "device", "update"):
        logger.warning(f"Permission denied for renaming device ({mac_address}).")
        return {"success": False, "error": "Permission denied to rename device."}

    try:
        # Fetch device details to provide context in the preview
        device = await device_manager.get_device_details(mac_address)
        if not device:
            return {
                "success": False,
                "error": f"Device not found with MAC address: {mac_address}",
            }

        # Extract device info for preview
        device_raw = device.raw if hasattr(device, "raw") else device
        current_name = device_raw.get("name", device_raw.get("model", "Unknown"))

        if not confirm and not should_auto_confirm():
            return update_preview(
                resource_type="device",
                resource_id=mac_address,
                resource_name=current_name,
                current_state={
                    "name": current_name,
                    "model": device_raw.get("model", ""),
                    "type": device_raw.get("type", ""),
                },
                updates={"name": name},
            )

        success = await device_manager.rename_device(mac_address, name)
        if success:
            return {
                "success": True,
                "message": f"Device {mac_address} renamed to '{name}' successfully.",
            }
        return {"success": False, "error": f"Failed to rename device {mac_address}."}
    except Exception as e:
        logger.error(f"Error renaming device {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_adopt_device",
    description="Adopt a pending device into the Unifi Network by MAC address",
    permission_category="devices",
    permission_action="create",
)
async def adopt_device(mac_address: str, confirm: bool = False) -> Dict[str, Any]:
    """Implementation for adopting a device."""
    if not parse_permission(config.permissions, "device", "adopt"):
        logger.warning(f"Permission denied for adopting device ({mac_address}).")
        return {"success": False, "error": "Permission denied to adopt device."}

    try:
        # Fetch device details to provide context in the preview
        device = await device_manager.get_device_details(mac_address)
        if not device:
            return {
                "success": False,
                "error": f"Device not found with MAC address: {mac_address}",
            }

        # Extract device info for preview
        device_raw = device.raw if hasattr(device, "raw") else device
        device_name = device_raw.get("name", device_raw.get("model", "Unknown"))
        device_state = device_raw.get("state", 0)

        if not confirm and not should_auto_confirm():
            return create_preview(
                resource_type="device_adoption",
                resource_name=device_name,
                resource_data={
                    "mac": mac_address,
                    "name": device_name,
                    "model": device_raw.get("model", ""),
                    "type": device_raw.get("type", ""),
                    "ip": device_raw.get("ip", ""),
                    "current_state": device_state,
                },
                warnings=[
                    "Device will be adopted into this site",
                    "Device may reboot during adoption process",
                ],
            )

        success = await device_manager.adopt_device(mac_address)
        if success:
            return {
                "success": True,
                "message": f"Adoption initiated for device: {mac_address}",
            }
        return {"success": False, "error": f"Failed to adopt device {mac_address}."}
    except Exception as e:
        logger.error(f"Error adopting device {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_upgrade_device",
    description="Initiate a firmware upgrade for a device by MAC address (uses cached firmware by default)",
    permission_category="devices",
    permission_action="update",
)
async def upgrade_device(mac_address: str, confirm: bool = False) -> Dict[str, Any]:
    """Implementation for upgrading a device."""
    if not parse_permission(config.permissions, "device", "upgrade"):
        logger.warning(f"Permission denied for upgrading device ({mac_address}).")
        return {"success": False, "error": "Permission denied to upgrade device."}

    try:
        # Fetch device details to provide context in the preview
        device = await device_manager.get_device_details(mac_address)
        if not device:
            return {
                "success": False,
                "error": f"Device not found with MAC address: {mac_address}",
            }

        # Extract device info for preview
        device_raw = device.raw if hasattr(device, "raw") else device
        device_name = device_raw.get("name", device_raw.get("model", "Unknown"))
        current_version = device_raw.get("version", "unknown")

        # Get upgrade information
        upgrade_info = device_raw.get("upgrade") or device_raw.get("upgradable")
        if isinstance(upgrade_info, bool):
            upgrade_info = "available" if upgrade_info else "none"

        upgrade_to_version = device_raw.get("upgrade_to_firmware", "latest available")

        if not confirm and not should_auto_confirm():
            return preview_response(
                action="upgrade",
                resource_type="device",
                resource_id=mac_address,
                resource_name=device_name,
                current_state={
                    "firmware_version": current_version,
                    "model": device_raw.get("model", ""),
                    "upgrade_available": upgrade_info,
                },
                proposed_changes={
                    "action": "firmware upgrade",
                    "target_version": upgrade_to_version,
                },
                warnings=[
                    "Device will be offline during firmware upgrade",
                    "Upgrade process may take several minutes",
                    "Do not power off device during upgrade",
                ],
            )

        success = await device_manager.upgrade_device(mac_address)
        if success:
            info_msg = f" (Upgrade info: {upgrade_info})" if upgrade_info else ""
            return {
                "success": True,
                "message": f"Upgrade initiated for device: {mac_address}{info_msg}",
            }
        return {"success": False, "error": f"Failed to upgrade device {mac_address}."}
    except Exception as e:
        logger.error(f"Error upgrading device {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


RADIO_BAND_LABELS = {"ng": "2.4GHz", "na": "5GHz", "6e": "6GHz", "wifi6e": "6GHz"}

VALID_RADIOS = {"na", "ng", "6e", "wifi6e"}
VALID_TX_POWER_MODES = {"auto", "high", "medium", "low", "custom"}
VALID_HT_VALUES = {"20", "40", "80", "160", "320"}


@server.tool(
    name="unifi_get_device_radio",
    description=(
        "Get radio configuration and live statistics for an access point. "
        "Returns per-band config (channel, tx_power, channel width, min_rssi) "
        "and live stats (actual tx_power, channel utilization, client count, retries)."
    ),
)
async def get_device_radio(mac_address: str) -> Dict[str, Any]:
    """Implementation for getting focused radio config and stats for an AP."""
    try:
        result = await device_manager.get_device_radio(mac_address)
        if result is None:
            return {
                "success": False,
                "error": f"Device {mac_address} not found or is not an access point.",
            }
        return {
            "success": True,
            "site": device_manager._connection.site,
            **result,
        }
    except Exception as e:
        logger.error(f"Error getting radio info for {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_update_device_radio",
    description=(
        "Update radio settings for a specific band on an access point. "
        "Supports tx_power_mode, tx_power (custom dBm), channel, ht (channel width), "
        "min_rssi_enabled, and min_rssi. Use unifi_get_device_radio first to see current settings."
    ),
    permission_category="devices",
    permission_action="update",
)
async def update_device_radio(
    mac_address: str,
    radio: str,
    tx_power_mode: str | None = None,
    tx_power: int | None = None,
    channel: int | None = None,
    ht: str | None = None,
    min_rssi_enabled: bool | None = None,
    min_rssi: int | None = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Implementation for updating AP radio settings."""
    if not parse_permission(config.permissions, "device", "update"):
        logger.warning(f"Permission denied for updating radio on device ({mac_address}).")
        return {"success": False, "error": "Permission denied to update device radio settings."}

    if radio not in VALID_RADIOS:
        return {
            "success": False,
            "error": f"Invalid radio '{radio}'. Must be one of: {', '.join(sorted(VALID_RADIOS))}",
        }

    if tx_power_mode is not None and tx_power_mode not in VALID_TX_POWER_MODES:
        return {
            "success": False,
            "error": f"Invalid tx_power_mode '{tx_power_mode}'. Must be one of: {', '.join(sorted(VALID_TX_POWER_MODES))}",
        }

    if tx_power is not None and tx_power_mode != "custom":
        return {"success": False, "error": "tx_power can only be set when tx_power_mode is 'custom'."}

    if ht is not None and ht not in VALID_HT_VALUES:
        return {"success": False, "error": f"Invalid ht '{ht}'. Must be one of: {', '.join(sorted(VALID_HT_VALUES))}"}

    if min_rssi is not None and min_rssi_enabled is not True:
        return {"success": False, "error": "min_rssi can only be set when min_rssi_enabled is true."}

    updates: Dict[str, Any] = {}
    if tx_power_mode is not None:
        updates["tx_power_mode"] = tx_power_mode
    if tx_power is not None:
        updates["tx_power"] = tx_power
    if channel is not None:
        updates["channel"] = channel
    if ht is not None:
        updates["ht"] = ht
    if min_rssi_enabled is not None:
        updates["min_rssi_enabled"] = min_rssi_enabled
    if min_rssi is not None:
        updates["min_rssi"] = min_rssi

    if not updates:
        return {"success": False, "error": "No radio settings provided to update."}

    try:
        radio_data = await device_manager.get_device_radio(mac_address)
        if radio_data is None:
            return {
                "success": False,
                "error": f"Device {mac_address} not found or is not an access point.",
            }

        target_radio = next((r for r in radio_data["radios"] if r["radio"] == radio or r["name"] == radio), None)
        if not target_radio:
            available = [
                f"{r['radio']} ({RADIO_BAND_LABELS.get(r['radio'], r['radio'])})" for r in radio_data["radios"]
            ]
            return {
                "success": False,
                "error": f"Radio '{radio}' not found on device. Available: {', '.join(available)}",
            }

        band_label = RADIO_BAND_LABELS.get(radio, radio)
        device_name = radio_data.get("name", mac_address)

        current_state = {k: target_radio.get(k) for k in updates}

        if not confirm and not should_auto_confirm():
            preview = update_preview(
                resource_type="device_radio",
                resource_id=f"{mac_address}/{radio}",
                resource_name=f"{device_name} ({band_label})",
                current_state=current_state,
                updates=updates,
            )
            preview["warnings"] = [
                "AP radio will restart briefly after changes are applied.",
                "Connected clients may experience a brief disconnection.",
            ]
            return preview

        success = await device_manager.update_device_radio(mac_address, radio, updates)
        if success:
            return {
                "success": True,
                "message": f"Radio '{radio}' ({band_label}) updated on {device_name} ({mac_address}).",
                "updated_fields": list(updates.keys()),
            }
        return {"success": False, "error": f"Failed to update radio '{radio}' on device {mac_address}."}
    except Exception as e:
        logger.error(f"Error updating radio on {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
