"""
Unifi Network MCP device management tools.

This module provides MCP tools to manage devices in a Unifi Network Controller.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Import the global FastMCP server instance, config, and managers
from src.runtime import server, config, device_manager
import mcp.types as types # Import the types module
from src.utils.permissions import parse_permission

logger = logging.getLogger(__name__)

def get_wifi_bands(device: Dict[str, Any]) -> List[str]:
    """Extract active WiFi bands from device radio table."""
    bands = set()
    for radio in device.get("radio_table", []):
        if radio.get("radio") == "na": bands.add("5GHz")
        elif radio.get("radio") == "ng": bands.add("2.4GHz")
        elif radio.get("radio") == "wifi6e": bands.add("6GHz")
    return sorted(list(bands))

@server.tool(
    name="unifi_list_devices",
    description="List devices adopted by the Unifi Network controller for the current site"
)
async def list_devices(
    device_type: str = "all",
    status: str = "all",
    include_details: bool = False
) -> Dict[str, Any]:
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
                    datetime.fromtimestamp(device.get("last_seen", 0)).isoformat()
                    if device.get("last_seen")
                    else "N/A"
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
                            "num_clients": device.get("user-num_sta", 0)
                            + device.get("guest-num_sta", 0),
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
                            "num_clients": device.get("user-num_sta", 0)
                            + device.get("guest-num_sta", 0),
                            "network_table": device.get("network_table", []),
                            "system_stats": device.get("system-stats", {}),
                            "speedtest_status": device.get("speedtest-status", {}),
                        }
                    )

                device_info.update(details_to_add)

            formatted_devices.append(device_info)
        
        return {
            "success": True, "site": device_manager._connection.site,
            "filter_type": device_type, "filter_status": status,
            "count": len(formatted_devices), "devices": formatted_devices
        }
    except Exception as e:
        logger.error(f"Error listing devices: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_get_device_details",
    description="Get detailed information about a specific device by MAC address"
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
        return {"success": False, "error": f"Device not found with MAC address: {mac_address}"}
    except Exception as e:
        logger.error(f"Error getting device details for {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_reboot_device",
    description="Reboot a specific device by MAC address"
)
async def reboot_device(mac_address: str, confirm: bool = False) -> Dict[str, Any]:
    """Implementation for rebooting a device."""
    if not parse_permission(config.permissions, "device", "reboot"):
        logger.warning(f"Permission denied for rebooting device ({mac_address}).")
        return {"success": False, "error": "Permission denied to reboot device."}
    
    if not confirm:
        return {"success": False, "error": "Confirmation required. Set confirm=true."}
    
    try:
        logger.info(f"Attempting to reboot device: {mac_address}")
        success = await device_manager.reboot_device(mac_address)
        
        if success:
            return {"success": True, "message": f"Reboot initiated for device: {mac_address}"}
        else:
            return {"success": False, "error": f"Failed to reboot device: {mac_address}"}
    except Exception as e:
        logger.error(f"Error rebooting device {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_rename_device",
    description="Rename a device in the Unifi Network controller by MAC address"
)
async def rename_device(mac_address: str, name: str, confirm: bool = False) -> Dict[str, Any]:
    """Implementation for renaming a device."""
    if not parse_permission(config.permissions, "device", "update"):
        logger.warning(f"Permission denied for renaming device ({mac_address}).")
        return {"success": False, "error": "Permission denied to rename device."}
    
    if not confirm:
        return {"success": False, "error": "Confirmation required. Set confirm=true."}
    
    try:
        success = await device_manager.rename_device(mac_address, name)
        if success:
            return {"success": True, "message": f"Device {mac_address} renamed to '{name}' successfully."}
        return {"success": False, "error": f"Failed to rename device {mac_address}."}
    except Exception as e:
        logger.error(f"Error renaming device {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_adopt_device",
    description="Adopt a pending device into the Unifi Network by MAC address"
)
async def adopt_device(mac_address: str, confirm: bool = False) -> Dict[str, Any]:
    """Implementation for adopting a device."""
    if not parse_permission(config.permissions, "device", "adopt"):
        logger.warning(f"Permission denied for adopting device ({mac_address}).")
        return {"success": False, "error": "Permission denied to adopt device."}
    
    if not confirm:
        return {"success": False, "error": "Confirmation required. Set confirm=true."}
    
    try:
        success = await device_manager.adopt_device(mac_address)
        if success:
            return {"success": True, "message": f"Adoption initiated for device: {mac_address}"}
        return {"success": False, "error": f"Failed to adopt device {mac_address}."}
    except Exception as e:
        logger.error(f"Error adopting device {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_upgrade_device",
    description="Initiate a firmware upgrade for a device by MAC address (uses cached firmware by default)"
)
async def upgrade_device(mac_address: str, confirm: bool = False) -> Dict[str, Any]:
    """Implementation for upgrading a device."""
    if not parse_permission(config.permissions, "device", "upgrade"):
        logger.warning(f"Permission denied for upgrading device ({mac_address}).")
        return {"success": False, "error": "Permission denied to upgrade device."}
    
    if not confirm:
        return {"success": False, "error": "Confirmation required. Set confirm=true."}
    
    try:
        upgrade_info = None
        try:
            device = await device_manager.get_device_details(mac_address)
            if device:
                upgrade_info = device.get("upgrade") or device.get("upgradable")
                if isinstance(upgrade_info, bool):
                    upgrade_info = "available" if upgrade_info else "none"
        except Exception as e:
            logger.warning(f"Could not fetch upgrade info for {mac_address}: {e}")
            
        success = await device_manager.upgrade_device(mac_address)
        if success:
            info_msg = f" (Upgrade info: {upgrade_info})" if upgrade_info else ""
            return {"success": True, "message": f"Upgrade initiated for device: {mac_address}{info_msg}"}
        return {"success": False, "error": f"Failed to upgrade device {mac_address}."}
    except Exception as e:
        logger.error(f"Error upgrading device {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)} 