"""
Unifi Network MCP client management tools.

This module provides MCP tools to manage network clients/devices on a Unifi Network Controller.
"""

import logging
import json
from typing import Dict, List, Any, Optional

# Import the global FastMCP server instance, config, and managers
from src.runtime import server, config, client_manager
import mcp.types as types # Import the types module
from src.utils.permissions import parse_permission

logger = logging.getLogger(__name__)

@server.tool(
    name="unifi_list_clients",
    description="List clients/devices connected to the Unifi Network"
)
async def list_clients(
    filter_type: str = "all", 
    include_offline: bool = False, 
    limit: int = 100
) -> Dict[str, Any]:
    """Implementation for listing clients."""
    try:
        clients = (
            await client_manager.get_all_clients() if include_offline else await client_manager.get_clients()
        )

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
                "status": "Online" if not include_offline else (
                    "Online" if client.get("is_wired", False) or (client.get("last_seen", 0) > 0) else "Offline"
                ),
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
    description="Get detailed information about a specific client/device by MAC address"
)
async def get_client_details(mac_address: str) -> Dict[str, Any]:
    """Implementation for getting client details."""
    try:
        client_obj = await client_manager.get_client_details(mac_address)
        if client_obj:
            client_raw = client_obj.raw if hasattr(client_obj, "raw") else client_obj
            return {"success": True, "site": client_manager._connection.site, "client": client_raw}
        return {"success": False, "error": f"Client not found with MAC address: {mac_address}"}
    except Exception as e:
        logger.error(f"Error getting client details for {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_list_blocked_clients",
    description="List clients/devices that are currently blocked from the network"
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
    description="Block a client/device from the network by MAC address"
)
async def block_client(mac_address: str, confirm: bool = False) -> Dict[str, Any]:
    """Implementation for blocking a client."""
    if not parse_permission(config.permissions, "client", "block"):
        logger.warning(f"Permission denied for blocking client ({mac_address}).")
        return {"success": False, "error": "Permission denied to block clients."}
    
    if not confirm:
        return {"success": False, "error": "Confirmation required. Set confirm=true."}
    
    try:
        success = await client_manager.block_client(mac_address)
        if success:
            return {"success": True, "message": f"Client {mac_address} blocked successfully."}
        return {"success": False, "error": f"Failed to block client {mac_address}."}
    except Exception as e:
        logger.error(f"Error blocking client {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_unblock_client",
    description="Unblock a previously blocked client/device by MAC address"
)
async def unblock_client(mac_address: str, confirm: bool = False) -> Dict[str, Any]:
    """Implementation for unblocking a client."""
    if not parse_permission(config.permissions, "client", "block"):
        logger.warning(f"Permission denied for unblocking client ({mac_address}).")
        return {"success": False, "error": "Permission denied to unblock clients."}
    
    if not confirm:
        return {"success": False, "error": "Confirmation required. Set confirm=true."}
    
    try:
        success = await client_manager.unblock_client(mac_address)
        if success:
            return {"success": True, "message": f"Client {mac_address} unblocked successfully."}
        return {"success": False, "error": f"Failed to unblock client {mac_address}."}
    except Exception as e:
        logger.error(f"Error unblocking client {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_rename_client",
    description="Rename a client/device in the Unifi Network controller by MAC address"
)
async def rename_client(mac_address: str, name: str, confirm: bool = False) -> Dict[str, Any]:
    """Implementation for renaming a client."""
    if not parse_permission(config.permissions, "client", "update"):
        logger.warning(f"Permission denied for renaming client ({mac_address}).")
        return {"success": False, "error": "Permission denied to rename clients."}
    
    if not confirm:
        return {"success": False, "error": "Confirmation required. Set confirm=true."}
    
    try:
        success = await client_manager.rename_client(mac_address, name)
        if success:
            return {"success": True, "message": f"Client {mac_address} renamed to '{name}' successfully."}
        return {"success": False, "error": f"Failed to rename client {mac_address}."}
    except Exception as e:
        logger.error(f"Error renaming client {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_force_reconnect_client",
    description="Force a client to reconnect to the network (kick) by MAC address"
)
async def force_reconnect_client(mac_address: str, confirm: bool = False) -> Dict[str, Any]:
    """Implementation for forcing a client to reconnect."""
    if not parse_permission(config.permissions, "client", "reconnect"):
        logger.warning(f"Permission denied for forcing reconnect of client ({mac_address}).")
        return {"success": False, "error": "Permission denied to force client reconnection."}
    
    if not confirm:
        return {"success": False, "error": "Confirmation required. Set confirm=true."}
    
    try:
        success = await client_manager.force_reconnect_client(mac_address)
        if success:
            return {"success": True, "message": f"Client {mac_address} reconnection forced successfully."}
        return {"success": False, "error": f"Failed to force reconnect for client {mac_address}."}
    except Exception as e:
        logger.error(f"Error forcing reconnect for client {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_authorize_guest",
    description="Authorize a guest client to access the guest network by MAC address"
)
async def authorize_guest(
    mac_address: str,
    minutes: int = 1440,
    up_kbps: Optional[int] = None,
    down_kbps: Optional[int] = None,
    bytes_quota: Optional[int] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """Implementation for authorizing a guest."""
    if not parse_permission(config.permissions, "client", "authorize"):
        logger.warning(f"Permission denied for authorizing guest ({mac_address}).")
        return {"success": False, "error": "Permission denied to authorize guests."}
    
    if not confirm:
        return {"success": False, "error": "Confirmation required. Set confirm=true."}
    
    try:
        success = await client_manager.authorize_guest(mac_address, minutes, up_kbps, down_kbps, bytes_quota)
        if success:
            return {"success": True, "message": f"Guest {mac_address} authorized successfully for {minutes} minutes."}
        return {"success": False, "error": f"Failed to authorize guest {mac_address}."}
    except Exception as e:
        logger.error(f"Error authorizing guest {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_unauthorize_guest",
    description="Revoke authorization for a guest client by MAC address"
)
async def unauthorize_guest(mac_address: str, confirm: bool = False) -> Dict[str, Any]:
    """Implementation for unauthorizing a guest."""
    if not parse_permission(config.permissions, "client", "authorize"):
        logger.warning(f"Permission denied for unauthorizing guest ({mac_address}).")
        return {"success": False, "error": "Permission denied to unauthorize guests."}
    
    if not confirm:
        return {"success": False, "error": "Confirmation required. Set confirm=true."}
    
    try:
        success = await client_manager.unauthorize_guest(mac_address)
        if success:
            return {"success": True, "message": f"Guest {mac_address} authorization revoked successfully."}
        return {"success": False, "error": f"Failed to unauthorize guest {mac_address}."}
    except Exception as e:
        logger.error(f"Error unauthorizing guest {mac_address}: {e}", exc_info=True)
        return {"success": False, "error": str(e)} 