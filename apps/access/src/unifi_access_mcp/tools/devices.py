"""Device tools for UniFi Access MCP server.

Provides tools for listing and inspecting Access hardware devices
(hubs, readers, relays, intercoms).
"""

import logging
from typing import Any, Dict

from mcp.types import ToolAnnotations

from unifi_access_mcp.runtime import device_manager, server

logger = logging.getLogger(__name__)


@server.tool(
    name="access_list_devices",
    description=(
        "Lists all Access hardware devices (hubs, readers, relays, intercoms) "
        "with their name, type, connection state, and firmware version."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def access_list_devices() -> Dict[str, Any]:
    """List all Access devices."""
    logger.info("access_list_devices tool called")
    try:
        devices = await device_manager.list_devices()
        return {"success": True, "data": {"devices": devices, "count": len(devices)}}
    except NotImplementedError:
        return {"success": False, "error": "Device listing not yet implemented"}
    except Exception as e:
        logger.error("Error listing devices: %s", e, exc_info=True)
        return {"success": False, "error": f"Failed to list devices: {e}"}


@server.tool(
    name="access_get_device",
    description="Returns detailed information for a single Access device.",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def access_get_device(device_id: str) -> Dict[str, Any]:
    """Get detailed device information by ID."""
    logger.info("access_get_device tool called for %s", device_id)
    try:
        detail = await device_manager.get_device(device_id)
        return {"success": True, "data": detail}
    except NotImplementedError:
        return {"success": False, "error": "Device detail not yet implemented"}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error("Error getting device %s: %s", device_id, e, exc_info=True)
        return {"success": False, "error": f"Failed to get device: {e}"}


logger.info("Device tools registered: access_list_devices, access_get_device")
