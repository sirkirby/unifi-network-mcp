"""
Unifi Network MCP client management tools.

This module provides MCP tools to manage network clients/devices on a Unifi Network Controller.
"""

import logging
from typing import Any, Dict, Optional

# Import the global FastMCP server instance, config, and managers
from src.runtime import client_manager, config, server
from src.utils.confirmation import should_auto_confirm, toggle_preview, update_preview
from src.utils.permissions import parse_permission

logger = logging.getLogger(__name__)


@server.tool(
    name="unifi_list_clients",
    description="List clients/devices connected to the Unifi Network",
)
async def list_clients(filter_type: str = "all", include_offline: bool = False, limit: int = 100) -> Dict[str, Any]:
    """Implementation for listing clients."""
    try:
        clients = await client_manager.get_all_clients() if include_offline else await client_manager.get_clients()

        def _client_to_dict(c):
            raw = c.raw if hasattr(c, "raw") else c  # c might already be a dict
            return raw

        clients_raw = [_client_to_dict(c) for c in clients]

        if filter_type == "wireless":
            clients_raw = [c for c in clients_raw if not c.get("is_wired", False)]
        elif filter_type == "wired":
            clients_raw = [c for c in clients_raw if c.get("is_wired", False)]

        clients_raw = clients_raw[:limit]

        formatted_clients = []
        for client in clients_raw:
            formatted = {
                "mac": client.get("mac"),
                "name": client.get("name") or client.get("hostname", "Unknown"),
                "hostname": client.get("hostname", "Unknown"),
                "ip": client.get("ip", "Unknown"),
                "connection_type": "Wired" if client.get("is_wired", False) else "Wireless",
                "status": "Online"
                if not include_offline
                else ("Online" if client.get("is_wired", False) or (client.get("last_seen", 0) > 0) else "Offline"),
                "last_seen": client.get("last_seen", 0),
                "_id": client.get("_id"),
            }

            if not client.get("is_wired", False):
                formatted.update(
                    {
                        "essid": client.get("essid", "Unknown"),
                        "signal_dbm": client.get("signal"),
                        "channel": client.get("channel", "Unknown"),
                        "radio": client.get("radio", "Unknown"),
                    }
                )

            formatted_clients.append(formatted)

        return {
            "success": True,
            "site": client_manager._connection.site,
            "count": len(formatted_clients),
            "clients": formatted_clients,
        }
    except Exception as e:
        logger.error(f"Error listing clients: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_get_client_details",
    description="Get detailed information about a specific client/device by MAC address",
)
async def get_client_details(mac_address: str) -> Dict[str, Any]:
    """Implementation for getting client details."""
    try:
        client_obj = await client_manager.get_client_details(mac_address)
        if client_obj:
            client_raw = client_obj.raw if hasattr(client_obj, "raw") else client_obj
            return {
                "success": True,
                "site": client_manager._connection.site,
                "client": client_raw,
            }
        return {
            "success": False,
            "error": f"Client not found with MAC address: {mac_address}",
        }
    except Exception as e:
        logger.error(f"Error getting client details for {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_list_blocked_clients",
    description="List clients/devices that are currently blocked from the network",
)
async def list_blocked_clients() -> Dict[str, Any]:
    """Implementation for listing blocked clients."""
    try:
        clients = await client_manager.get_blocked_clients()

        formatted_clients = []
        for c in clients:
            client = c.raw if hasattr(c, "raw") else c

            formatted_clients.append(
                {
                    "mac": client.get("mac"),
                    "name": client.get("name") or client.get("hostname", "Unknown"),
                    "hostname": client.get("hostname", "Unknown"),
                    "ip": client.get("ip", "Unknown"),
                    "connection_type": "Wired" if client.get("is_wired", False) else "Wireless",
                    "blocked_since": client.get("blocked_since", 0),
                    "_id": client.get("_id"),
                }
            )

        return {
            "success": True,
            "site": client_manager._connection.site,
            "count": len(formatted_clients),
            "blocked_clients": formatted_clients,
        }
    except Exception as e:
        logger.error(f"Error listing blocked clients: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_block_client",
    description="Block a client/device from the network by MAC address",
    permission_category="clients",
    permission_action="update",
)
async def block_client(mac_address: str, confirm: bool = False) -> Dict[str, Any]:
    """Implementation for blocking a client."""
    if not parse_permission(config.permissions, "client", "block"):
        logger.warning(f"Permission denied for blocking client ({mac_address}).")
        return {"success": False, "error": "Permission denied to block clients."}

    try:
        # Fetch client details first
        client_obj = await client_manager.get_client_details(mac_address)
        if not client_obj:
            return {
                "success": False,
                "error": f"Client not found with MAC address: {mac_address}",
            }

        client = client_obj.raw if hasattr(client_obj, "raw") else client_obj
        client_name = client.get("name") or client.get("hostname", "Unknown")
        is_blocked = client.get("blocked", False)

        # Return preview when confirm=false
        if not confirm and not should_auto_confirm():
            return toggle_preview(
                resource_type="client",
                resource_id=mac_address,
                resource_name=client_name,
                current_enabled=not is_blocked,  # enabled = not blocked
                additional_info={
                    "ip": client.get("ip"),
                    "hostname": client.get("hostname"),
                    "action": "block",
                },
            )

        success = await client_manager.block_client(mac_address)
        if success:
            return {
                "success": True,
                "message": f"Client {mac_address} blocked successfully.",
            }
        return {"success": False, "error": f"Failed to block client {mac_address}."}
    except Exception as e:
        logger.error(f"Error blocking client {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_unblock_client",
    description="Unblock a previously blocked client/device by MAC address",
    permission_category="clients",
    permission_action="update",
)
async def unblock_client(mac_address: str, confirm: bool = False) -> Dict[str, Any]:
    """Implementation for unblocking a client."""
    if not parse_permission(config.permissions, "client", "block"):
        logger.warning(f"Permission denied for unblocking client ({mac_address}).")
        return {"success": False, "error": "Permission denied to unblock clients."}

    try:
        # Fetch client details first
        client_obj = await client_manager.get_client_details(mac_address)
        if not client_obj:
            return {
                "success": False,
                "error": f"Client not found with MAC address: {mac_address}",
            }

        client = client_obj.raw if hasattr(client_obj, "raw") else client_obj
        client_name = client.get("name") or client.get("hostname", "Unknown")
        is_blocked = client.get("blocked", False)

        # Return preview when confirm=false
        if not confirm and not should_auto_confirm():
            return toggle_preview(
                resource_type="client",
                resource_id=mac_address,
                resource_name=client_name,
                current_enabled=not is_blocked,  # enabled = not blocked
                additional_info={
                    "ip": client.get("ip"),
                    "hostname": client.get("hostname"),
                    "action": "unblock",
                },
            )

        success = await client_manager.unblock_client(mac_address)
        if success:
            return {
                "success": True,
                "message": f"Client {mac_address} unblocked successfully.",
            }
        return {"success": False, "error": f"Failed to unblock client {mac_address}."}
    except Exception as e:
        logger.error(f"Error unblocking client {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_rename_client",
    description="Rename a client/device in the Unifi Network controller by MAC address",
)
async def rename_client(mac_address: str, name: str, confirm: bool = False) -> Dict[str, Any]:
    """Implementation for renaming a client."""
    if not parse_permission(config.permissions, "client", "update"):
        logger.warning(f"Permission denied for renaming client ({mac_address}).")
        return {"success": False, "error": "Permission denied to rename clients."}

    try:
        # Fetch client details first
        client_obj = await client_manager.get_client_details(mac_address)
        if not client_obj:
            return {
                "success": False,
                "error": f"Client not found with MAC address: {mac_address}",
            }

        client = client_obj.raw if hasattr(client_obj, "raw") else client_obj
        current_name = client.get("name") or client.get("hostname", "Unknown")

        # Return preview when confirm=false
        if not confirm and not should_auto_confirm():
            return update_preview(
                resource_type="client",
                resource_id=mac_address,
                resource_name=current_name,
                current_state={"name": current_name},
                updates={"name": name},
            )

        success = await client_manager.rename_client(mac_address, name)
        if success:
            return {
                "success": True,
                "message": f"Client {mac_address} renamed to '{name}' successfully.",
            }
        return {"success": False, "error": f"Failed to rename client {mac_address}."}
    except Exception as e:
        logger.error(f"Error renaming client {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_force_reconnect_client",
    description="Force a client to reconnect to the network (kick) by MAC address",
    permission_category="clients",
    permission_action="update",
)
async def force_reconnect_client(mac_address: str, confirm: bool = False) -> Dict[str, Any]:
    """Implementation for forcing a client to reconnect."""
    if not parse_permission(config.permissions, "client", "reconnect"):
        logger.warning(f"Permission denied for forcing reconnect of client ({mac_address}).")
        return {
            "success": False,
            "error": "Permission denied to force client reconnection.",
        }

    try:
        # Fetch client details first
        client_obj = await client_manager.get_client_details(mac_address)
        if not client_obj:
            return {
                "success": False,
                "error": f"Client not found with MAC address: {mac_address}",
            }

        client = client_obj.raw if hasattr(client_obj, "raw") else client_obj
        client_name = client.get("name") or client.get("hostname", "Unknown")

        # Return preview when confirm=false
        if not confirm and not should_auto_confirm():
            return {
                "success": False,
                "requires_confirmation": True,
                "action": "force_reconnect",
                "resource_type": "client",
                "resource_id": mac_address,
                "resource_name": client_name,
                "preview": {
                    "current": {
                        "ip": client.get("ip"),
                        "hostname": client.get("hostname"),
                        "connection_type": "Wired" if client.get("is_wired") else "Wireless",
                    },
                    "action": "Client will be disconnected and forced to reconnect",
                },
                "message": f"Will force reconnect for client '{client_name}'. Set confirm=true to execute.",
            }

        success = await client_manager.force_reconnect_client(mac_address)
        if success:
            return {
                "success": True,
                "message": f"Client {mac_address} reconnection forced successfully.",
            }
        return {
            "success": False,
            "error": f"Failed to force reconnect for client {mac_address}.",
        }
    except Exception as e:
        logger.error(f"Error forcing reconnect for client {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_authorize_guest",
    description="Authorize a guest client to access the guest network by MAC address",
    permission_category="clients",
    permission_action="update",
)
async def authorize_guest(
    mac_address: str,
    minutes: int = 1440,
    up_kbps: Optional[int] = None,
    down_kbps: Optional[int] = None,
    bytes_quota: Optional[int] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Implementation for authorizing a guest."""
    if not parse_permission(config.permissions, "client", "authorize"):
        logger.warning(f"Permission denied for authorizing guest ({mac_address}).")
        return {"success": False, "error": "Permission denied to authorize guests."}

    try:
        # Fetch client details first
        client_obj = await client_manager.get_client_details(mac_address)
        if not client_obj:
            return {
                "success": False,
                "error": f"Client not found with MAC address: {mac_address}",
            }

        client = client_obj.raw if hasattr(client_obj, "raw") else client_obj
        client_name = client.get("name") or client.get("hostname", "Unknown")

        # Return preview when confirm=false
        if not confirm and not should_auto_confirm():
            settings = {"minutes": minutes}
            if up_kbps is not None:
                settings["up_kbps"] = up_kbps
            if down_kbps is not None:
                settings["down_kbps"] = down_kbps
            if bytes_quota is not None:
                settings["bytes_quota"] = bytes_quota

            return {
                "success": False,
                "requires_confirmation": True,
                "action": "authorize_guest",
                "resource_type": "client",
                "resource_id": mac_address,
                "resource_name": client_name,
                "preview": {
                    "current": {
                        "ip": client.get("ip"),
                        "hostname": client.get("hostname"),
                    },
                    "proposed": settings,
                },
                "message": f"Will authorize guest '{client_name}' for {minutes} minutes. Set confirm=true to execute.",
            }

        success = await client_manager.authorize_guest(mac_address, minutes, up_kbps, down_kbps, bytes_quota)
        if success:
            return {
                "success": True,
                "message": f"Guest {mac_address} authorized successfully for {minutes} minutes.",
            }
        return {"success": False, "error": f"Failed to authorize guest {mac_address}."}
    except Exception as e:
        logger.error(f"Error authorizing guest {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_unauthorize_guest",
    description="Revoke authorization for a guest client by MAC address",
    permission_category="clients",
    permission_action="update",
)
async def unauthorize_guest(mac_address: str, confirm: bool = False) -> Dict[str, Any]:
    """Implementation for unauthorizing a guest."""
    if not parse_permission(config.permissions, "client", "authorize"):
        logger.warning(f"Permission denied for unauthorizing guest ({mac_address}).")
        return {"success": False, "error": "Permission denied to unauthorize guests."}

    try:
        # Fetch client details first
        client_obj = await client_manager.get_client_details(mac_address)
        if not client_obj:
            return {
                "success": False,
                "error": f"Client not found with MAC address: {mac_address}",
            }

        client = client_obj.raw if hasattr(client_obj, "raw") else client_obj
        client_name = client.get("name") or client.get("hostname", "Unknown")

        # Return preview when confirm=false
        if not confirm and not should_auto_confirm():
            return {
                "success": False,
                "requires_confirmation": True,
                "action": "unauthorize_guest",
                "resource_type": "client",
                "resource_id": mac_address,
                "resource_name": client_name,
                "preview": {
                    "current": {
                        "ip": client.get("ip"),
                        "hostname": client.get("hostname"),
                    },
                    "action": "Guest authorization will be revoked",
                },
                "message": f"Will revoke guest authorization for '{client_name}'. Set confirm=true to execute.",
            }

        success = await client_manager.unauthorize_guest(mac_address)
        if success:
            return {
                "success": True,
                "message": f"Guest {mac_address} authorization revoked successfully.",
            }
        return {
            "success": False,
            "error": f"Failed to unauthorize guest {mac_address}.",
        }
    except Exception as e:
        logger.error(f"Error unauthorizing guest {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_set_client_ip_settings",
    description="""Set fixed IP address and/or local DNS record for a client device.

Allows configuring:
- Fixed IP: Assign a static IP address to a client (DHCP reservation)
- Local DNS: Create a local DNS hostname for the client (UniFi Network 7.2+)

Either setting can be enabled/disabled independently.""",
    permission_category="clients",
    permission_action="update",
)
async def set_client_ip_settings(
    mac_address: str,
    use_fixedip: bool | None = None,
    fixed_ip: str | None = None,
    local_dns_record_enabled: bool | None = None,
    local_dns_record: str | None = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Set fixed IP and/or local DNS record for a client."""
    if not parse_permission(config.permissions, "client", "update"):
        logger.warning(f"Permission denied for setting IP settings ({mac_address}).")
        return {
            "success": False,
            "error": "Permission denied to update client settings.",
        }

    # Validate that at least one setting is provided
    if all(v is None for v in [use_fixedip, fixed_ip, local_dns_record_enabled, local_dns_record]):
        return {
            "success": False,
            "error": "At least one setting must be provided (use_fixedip, fixed_ip, local_dns_record_enabled, or local_dns_record).",
        }

    try:
        # Fetch client details first
        client_obj = await client_manager.get_client_details(mac_address)
        if not client_obj:
            return {
                "success": False,
                "error": f"Client not found with MAC address: {mac_address}",
            }

        client = client_obj.raw if hasattr(client_obj, "raw") else client_obj
        client_name = client.get("name") or client.get("hostname", "Unknown")

        # Return preview when confirm=false
        if not confirm and not should_auto_confirm():
            # Build current state from the client object
            current_state = {
                "use_fixedip": client.get("use_fixedip", False),
                "fixed_ip": client.get("fixed_ip"),
                "local_dns_record_enabled": client.get("local_dns_record_enabled", False),
                "local_dns_record": client.get("local_dns_record"),
            }

            # Build updates dict with only provided values
            updates = {}
            if use_fixedip is not None:
                updates["use_fixedip"] = use_fixedip
            if fixed_ip is not None:
                updates["fixed_ip"] = fixed_ip
            if local_dns_record_enabled is not None:
                updates["local_dns_record_enabled"] = local_dns_record_enabled
            if local_dns_record is not None:
                updates["local_dns_record"] = local_dns_record

            return update_preview(
                resource_type="client",
                resource_id=mac_address,
                resource_name=client_name,
                current_state=current_state,
                updates=updates,
            )

        success = await client_manager.set_client_ip_settings(
            client_mac=mac_address,
            use_fixedip=use_fixedip,
            fixed_ip=fixed_ip,
            local_dns_record_enabled=local_dns_record_enabled,
            local_dns_record=local_dns_record,
        )
        if success:
            return {
                "success": True,
                "message": f"IP settings updated for client {mac_address}.",
                "settings": {
                    k: v
                    for k, v in {
                        "use_fixedip": use_fixedip,
                        "fixed_ip": fixed_ip,
                        "local_dns_record_enabled": local_dns_record_enabled,
                        "local_dns_record": local_dns_record,
                    }.items()
                    if v is not None
                },
            }
        return {
            "success": False,
            "error": f"Failed to update IP settings for client {mac_address}.",
        }
    except Exception as e:
        logger.error(f"Error setting IP settings for {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
