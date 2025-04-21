"""
VPN configuration tools for Unifi Network MCP server.

This module provides MCP tools to interact with a Unifi Network Controller's VPN functions,
including managing VPN clients and servers.
"""

import logging
import json
from typing import Dict, List, Any, Optional

from src.runtime import server, config, vpn_manager
import mcp.types as types # Import the types module
from src.utils.permissions import parse_permission

logger = logging.getLogger(__name__)

@server.tool(
    name="unifi_list_vpn_clients",
    description="List all configured VPN clients (Wireguard, OpenVPN, etc)."
)
async def list_vpn_clients() -> Dict[str, Any]:
    """Implementation for listing VPN clients."""
    if not parse_permission(config.permissions, "vpn_client", "read"):
        logger.warning("Permission denied for listing VPN clients.")
        return {"success": False, "error": "Permission denied to list VPN clients."}
    try:
        clients = await vpn_manager.get_vpn_clients()
        return {"success": True, "site": vpn_manager._connection.site, "count": len(clients), "vpn_clients": clients}
    except Exception as e:
        logger.error(f"Error listing VPN clients: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_get_vpn_client_details",
    description="Get details for a specific VPN client by ID."
)
async def get_vpn_client_details(client_id: str) -> Dict[str, Any]:
    """Implementation for getting VPN client details."""
    if not parse_permission(config.permissions, "vpn_client", "read"):
        logger.warning(f"Permission denied for getting VPN client details ({client_id}).")
        return {"success": False, "error": "Permission denied to get VPN client details."}
    try:
        client = await vpn_manager.get_vpn_client_details(client_id)
        if client: 
            return {"success": True, "site": vpn_manager._connection.site, "client_id": client_id, "details": client}
        else: 
            return {"success": False, "error": f"VPN client '{client_id}' not found."}
    except Exception as e:
        logger.error(f"Error getting VPN client details for {client_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_update_vpn_client_state",
    description="Enable or disable a specific VPN client by ID."
)
async def update_vpn_client_state(client_id: str, enabled: bool) -> Dict[str, Any]:
    """Implementation for updating VPN client state."""
    if not parse_permission(config.permissions, "vpn_client", "update"):
        logger.warning(f"Permission denied for updating VPN client state ({client_id}).")
        return {"success": False, "error": "Permission denied to update VPN client state."}
    try:
        success = await vpn_manager.update_vpn_client_state(client_id, enabled)
        if success:
            client_details = await vpn_manager.get_vpn_client_details(client_id)
            name = client_details.get("name", client_id) if client_details else client_id
            state = "enabled" if enabled else "disabled"
            return {"success": True, "message": f"VPN client '{name}' ({client_id}) {state}."}
        else:
             client_details = await vpn_manager.get_vpn_client_details(client_id)
             name = client_details.get("name", client_id) if client_details else client_id
             return {"success": False, "error": f"Failed to update state for VPN client '{name}'."}
    except Exception as e:
        logger.error(f"Error updating state for VPN client {client_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_list_vpn_servers",
    description="List all configured VPN servers (Wireguard, OpenVPN, L2TP, etc)."
)
async def list_vpn_servers() -> Dict[str, Any]:
    """Implementation for listing VPN servers."""
    if not parse_permission(config.permissions, "vpn_server", "read"):
        logger.warning("Permission denied for listing VPN servers.")
        return {"success": False, "error": "Permission denied to list VPN servers."}
    try:
        servers = await vpn_manager.get_vpn_servers()
        return {"success": True, "site": vpn_manager._connection.site, "count": len(servers), "vpn_servers": servers}
    except Exception as e:
        logger.error(f"Error listing VPN servers: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_get_vpn_server_details",
    description="Get details for a specific VPN server by ID."
)
async def get_vpn_server_details(server_id: str) -> Dict[str, Any]:
    """Implementation for getting VPN server details."""
    if not parse_permission(config.permissions, "vpn_server", "read"):
        logger.warning(f"Permission denied for getting VPN server details ({server_id}).")
        return {"success": False, "error": "Permission denied to get VPN server details."}
    try:
        server = await vpn_manager.get_vpn_server_details(server_id)
        if server: 
            return {"success": True, "site": vpn_manager._connection.site, "server_id": server_id, "details": server}
        else: 
            return {"success": False, "error": f"VPN server '{server_id}' not found."}
    except Exception as e:
        logger.error(f"Error getting VPN server details for {server_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_update_vpn_server_state",
    description="Enable or disable a specific VPN server by ID."
)
async def update_vpn_server_state(server_id: str, enabled: bool) -> Dict[str, Any]:
    """Implementation for updating VPN server state."""
    if not parse_permission(config.permissions, "vpn_server", "update"):
        logger.warning(f"Permission denied for updating VPN server state ({server_id}).")
        return {"success": False, "error": "Permission denied to update VPN server state."}
    try:
        success = await vpn_manager.update_vpn_server_state(server_id, enabled)
        if success:
            server_details = await vpn_manager.get_vpn_server_details(server_id)
            name = server_details.get("name", server_id) if server_details else server_id
            state = "enabled" if enabled else "disabled"
            return {"success": True, "message": f"VPN server '{name}' ({server_id}) {state}."}
        else:
            server_details = await vpn_manager.get_vpn_server_details(server_id)
            name = server_details.get("name", server_id) if server_details else server_id
            return {"success": False, "error": f"Failed to update state for VPN server '{name}'."}
    except Exception as e:
        logger.error(f"Error updating state for VPN server {server_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}