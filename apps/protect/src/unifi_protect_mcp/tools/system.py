"""System tools for UniFi Protect MCP server.

Provides read-only tools for querying NVR system info, health,
connected viewers, and firmware update status.
"""

import logging
from typing import Any, Dict

from mcp.types import ToolAnnotations

from unifi_protect_mcp.runtime import server, system_manager

logger = logging.getLogger(__name__)


@server.tool(
    name="protect_get_system_info",
    description=(
        "Returns NVR model, firmware version, uptime, storage usage, and connected device counts. "
        "Use for basic 'is the NVR healthy?' checks and capacity overview."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def protect_get_system_info() -> Dict[str, Any]:
    """Get Protect NVR system information."""
    logger.info("protect_get_system_info tool called")
    try:
        info = await system_manager.get_system_info()
        return {"success": True, "data": info}
    except Exception as e:
        logger.error("Error getting system info: %s", e, exc_info=True)
        return {"success": False, "error": f"Failed to get system info: {e}"}


@server.tool(
    name="protect_get_health",
    description=(
        "Returns NVR health summary including CPU load and temperature, memory usage, "
        "and storage utilization. Use to diagnose performance issues or storage pressure."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def protect_get_health() -> Dict[str, Any]:
    """Get Protect NVR health metrics."""
    logger.info("protect_get_health tool called")
    try:
        health = await system_manager.get_health()
        return {"success": True, "data": health}
    except Exception as e:
        logger.error("Error getting health: %s", e, exc_info=True)
        return {"success": False, "error": f"Failed to get health: {e}"}


@server.tool(
    name="protect_list_viewers",
    description=(
        "Lists all connected Protect viewers (e.g., UP-Viewer, Viewport) with their "
        "connection state, firmware version, and assigned liveview."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def protect_list_viewers() -> Dict[str, Any]:
    """List connected Protect viewers."""
    logger.info("protect_list_viewers tool called")
    try:
        viewers = await system_manager.list_viewers()
        return {"success": True, "data": {"viewers": viewers, "count": len(viewers)}}
    except Exception as e:
        logger.error("Error listing viewers: %s", e, exc_info=True)
        return {"success": False, "error": f"Failed to list viewers: {e}"}


@server.tool(
    name="protect_get_firmware_status",
    description=(
        "Returns firmware update availability for the NVR and all adopted devices "
        "(cameras, lights, sensors, viewers, chimes, bridges, doorlocks). "
        "Use to check whether any device needs a firmware update."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def protect_get_firmware_status() -> Dict[str, Any]:
    """Get firmware status for NVR and devices."""
    logger.info("protect_get_firmware_status tool called")
    try:
        status = await system_manager.get_firmware_status()
        return {"success": True, "data": status}
    except Exception as e:
        logger.error("Error getting firmware status: %s", e, exc_info=True)
        return {"success": False, "error": f"Failed to get firmware status: {e}"}


logger.info(
    "System tools registered: protect_get_system_info, protect_get_health, "
    "protect_list_viewers, protect_get_firmware_status"
)
