"""
Unifi Network MCP system tools.

This module provides MCP tools to interact with a Unifi Network Controller's system functions.
"""

import logging
import json
from typing import Dict, List, Any, Optional

from src.runtime import server, config, system_manager, client_manager
import mcp.types as types # Import the types module
from src.utils.permissions import parse_permission

logger = logging.getLogger(__name__)

# Explicitly retrieve and log the server instance to confirm it's being used
logger.info(f"System tools module loaded, server instance: {server}")

@server.tool(
    name="unifi_get_system_info",
    description="Get general system information from the Unifi Network controller (version, uptime, etc)."
)
async def get_system_info() -> Dict[str, Any]:
    """Implementation for getting system info."""
    logger.info("unifi_get_system_info tool called")
    try:
        info = await system_manager.get_system_info()
        return {"success": True, "site": system_manager._connection.site, "system_info": info}
    except Exception as e:
        logger.error(f"Error getting system info: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_get_network_health",
    description="Get the current network health summary (WAN status, device counts)."
)
async def get_network_health() -> Dict[str, Any]:
    """Implementation for getting network health."""
    logger.info("unifi_get_network_health tool called")
    try:
        health = await system_manager.get_network_health()
        return {"success": True, "site": system_manager._connection.site, "health_summary": health}
    except Exception as e:
        logger.error(f"Error getting network health: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_get_site_settings",
    description="Get current site settings (e.g., country code, timezone, connectivity monitoring)."
)
async def get_site_settings() -> Dict[str, Any]:
    """Implementation for getting site settings."""
    logger.info("unifi_get_site_settings tool called")
    try:
        settings = await system_manager.get_site_settings()
        return {"success": True, "site": system_manager._connection.site, "site_settings": settings}
    except Exception as e:
        logger.error(f"Error getting site settings: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

# Print confirmation that all tools have been registered
logger.info("System tools registered: unifi_get_system_info, unifi_get_network_health, unifi_get_site_settings")