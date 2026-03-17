"""Door tools for UniFi Access MCP server.

Provides tools for listing, inspecting, locking, and unlocking doors.
"""

import logging
from typing import Any, Dict

from mcp.types import ToolAnnotations

from unifi_access_mcp.runtime import door_manager, server

logger = logging.getLogger(__name__)


@server.tool(
    name="access_list_doors",
    description=(
        "Lists all doors managed by the Access controller with their name, "
        "lock state, and connection status. Use to get an overview of all doors."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def access_list_doors() -> Dict[str, Any]:
    """List all doors."""
    logger.info("access_list_doors tool called")
    try:
        doors = await door_manager.list_doors()
        return {"success": True, "data": {"doors": doors, "count": len(doors)}}
    except NotImplementedError:
        return {"success": False, "error": "Door listing not yet implemented"}
    except Exception as e:
        logger.error("Error listing doors: %s", e, exc_info=True)
        return {"success": False, "error": f"Failed to list doors: {e}"}


@server.tool(
    name="access_get_door",
    description=(
        "Returns detailed information for a single door including lock state, "
        "configuration, and connected devices."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def access_get_door(door_id: str) -> Dict[str, Any]:
    """Get detailed door information by ID."""
    logger.info("access_get_door tool called for %s", door_id)
    try:
        detail = await door_manager.get_door(door_id)
        return {"success": True, "data": detail}
    except NotImplementedError:
        return {"success": False, "error": "Door detail not yet implemented"}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error("Error getting door %s: %s", door_id, e, exc_info=True)
        return {"success": False, "error": f"Failed to get door: {e}"}


logger.info("Door tools registered: access_list_doors, access_get_door")
