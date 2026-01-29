"""
Unifi Network MCP system tools.

This module provides MCP tools to interact with a Unifi Network Controller's system functions.
"""

import logging
from typing import Any, Dict, Optional

from src.runtime import config, server, system_manager
from src.utils.confirmation import should_auto_confirm, update_preview
from src.utils.permissions import parse_permission

logger = logging.getLogger(__name__)

# Explicitly retrieve and log the server instance to confirm it's being used
logger.info(f"System tools module loaded, server instance: {server}")


@server.tool(
    name="unifi_get_system_info",
    description="Get general system information from the Unifi Network controller (version, uptime, etc).",
)
async def get_system_info() -> Dict[str, Any]:
    """Implementation for getting system info."""
    logger.info("unifi_get_system_info tool called")
    try:
        info = await system_manager.get_system_info()
        return {
            "success": True,
            "site": system_manager._connection.site,
            "system_info": info,
        }
    except Exception as e:
        logger.error(f"Error getting system info: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_get_network_health",
    description="Get the current network health summary (WAN status, device counts).",
)
async def get_network_health() -> Dict[str, Any]:
    """Implementation for getting network health."""
    logger.info("unifi_get_network_health tool called")
    try:
        health = await system_manager.get_network_health()
        return {
            "success": True,
            "site": system_manager._connection.site,
            "health_summary": health,
        }
    except Exception as e:
        logger.error(f"Error getting network health: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_get_site_settings",
    description="Get current site settings (e.g., country code, timezone, connectivity monitoring).",
)
async def get_site_settings() -> Dict[str, Any]:
    """Implementation for getting site settings."""
    logger.info("unifi_get_site_settings tool called")
    try:
        settings = await system_manager.get_site_settings()
        return {
            "success": True,
            "site": system_manager._connection.site,
            "site_settings": settings,
        }
    except Exception as e:
        logger.error(f"Error getting site settings: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_get_snmp_settings",
    description="Get current SNMP settings for the site (enabled state, community string).",
)
async def get_snmp_settings() -> Dict[str, Any]:
    """Implementation for getting SNMP settings."""
    logger.info("unifi_get_snmp_settings tool called")
    try:
        settings_list = await system_manager.get_settings("snmp")
        snmp_settings = settings_list[0] if settings_list else {}
        return {
            "success": True,
            "site": system_manager._connection.site,
            "snmp_settings": {
                "enabled": snmp_settings.get("enabled", False),
                "community": snmp_settings.get("community", ""),
            },
        }
    except Exception as e:
        logger.error(f"Error getting SNMP settings: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_update_snmp_settings",
    description="Update SNMP settings for the site (enable/disable, set community string). Requires confirm=true to apply changes.",
)
async def update_snmp_settings(
    enabled: bool,
    community: Optional[str] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Implementation for updating SNMP settings.

    Args:
        enabled: Whether SNMP should be enabled on the site.
        community: SNMP community string (optional, keeps current value if not provided).
        confirm: Must be true to apply changes. When false, returns a preview of proposed changes.
    """
    logger.info(f"unifi_update_snmp_settings tool called (enabled={enabled}, confirm={confirm})")

    if not parse_permission(config.permissions, "snmp", "update"):
        logger.warning("Permission denied for updating SNMP settings.")
        return {"success": False, "error": "Permission denied to update SNMP settings."}

    try:
        settings_list = await system_manager.get_settings("snmp")
        current = settings_list[0] if settings_list else {}

        updates: Dict[str, Any] = {"enabled": enabled}
        if community is not None:
            updates["community"] = community

        if not confirm and not should_auto_confirm():
            return update_preview(
                resource_type="snmp_settings",
                resource_id=current.get("_id", "snmp"),
                resource_name="SNMP Settings",
                current_state={
                    "enabled": current.get("enabled", False),
                    "community": current.get("community", ""),
                },
                updates=updates,
            )

        payload: Dict[str, Any] = {"enabled": enabled}
        if community is not None:
            payload["community"] = community

        success = await system_manager.update_settings("snmp", payload)
        if success:
            refreshed = await system_manager.get_settings("snmp")
            new_settings = refreshed[0] if refreshed else payload
            return {
                "success": True,
                "site": system_manager._connection.site,
                "snmp_settings": {
                    "enabled": new_settings.get("enabled", enabled),
                    "community": new_settings.get("community", community or ""),
                },
            }
        return {"success": False, "error": "Failed to update SNMP settings."}
    except Exception as e:
        logger.error(f"Error updating SNMP settings: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# Print confirmation that all tools have been registered
logger.info(
    "System tools registered: unifi_get_system_info, unifi_get_network_health, "
    "unifi_get_site_settings, unifi_get_snmp_settings, unifi_update_snmp_settings"
)
