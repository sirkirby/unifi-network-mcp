"""Liveview tools for UniFi Protect MCP server.

Provides tools for listing, creating, and deleting liveview configurations.
Liveviews are multi-camera layout configurations for the Protect app and
UniFi Viewport devices.
"""

import logging
from typing import Any, Dict, List

from mcp.types import ToolAnnotations

from unifi_protect_mcp.runtime import liveview_manager, server

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Read-only tools
# ---------------------------------------------------------------------------


@server.tool(
    name="protect_list_liveviews",
    description=(
        "Lists all liveview configurations from the Protect NVR. Each liveview "
        "defines a multi-camera layout with slots, camera assignments, and cycle "
        "settings. Shows name, layout grid size, slot count, camera count, and "
        "whether it is the default or global view."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def protect_list_liveviews() -> Dict[str, Any]:
    """List all liveviews."""
    logger.info("protect_list_liveviews tool called")
    try:
        liveviews = await liveview_manager.list_liveviews()
        return {"success": True, "data": {"liveviews": liveviews, "count": len(liveviews)}}
    except Exception as e:
        logger.error("Error listing liveviews: %s", e, exc_info=True)
        return {"success": False, "error": f"Failed to list liveviews: {e}"}


# ---------------------------------------------------------------------------
# Mutation tools
# ---------------------------------------------------------------------------


@server.tool(
    name="protect_create_liveview",
    description=(
        "Validates input for creating a new liveview with the given name and "
        "camera IDs. Note: liveview creation is not directly supported by the "
        "uiprotect Python API; this tool validates camera IDs and returns a "
        "preview. Use the Protect web UI to create liveviews."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=False),
    permission_category="liveview",
    permission_action="create",
)
async def protect_create_liveview(
    name: str,
    camera_ids: List[str],
    confirm: bool = False,
) -> Dict[str, Any]:
    """Create a liveview (validation only -- API limitation)."""
    logger.info("protect_create_liveview called (name=%s, cameras=%d)", name, len(camera_ids))
    try:
        if not name:
            return {"success": False, "error": "Liveview name is required."}
        if not camera_ids:
            return {"success": False, "error": "At least one camera ID is required."}

        result = await liveview_manager.create_liveview(name=name, camera_ids=camera_ids)

        # Since creation is not supported via uiprotect, return info regardless of confirm
        return {"success": False, "error": result["message"], "data": result}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error("Error creating liveview: %s", e, exc_info=True)
        return {"success": False, "error": f"Failed to create liveview: {e}"}


@server.tool(
    name="protect_delete_liveview",
    description=(
        "Validates a liveview for deletion by ID. Note: liveview deletion is not "
        "directly supported by the uiprotect Python API; this tool returns "
        "information about the liveview. Use the Protect web UI to delete liveviews."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=False),
    permission_category="liveview",
    permission_action="delete",
)
async def protect_delete_liveview(
    liveview_id: str,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Delete a liveview (not supported via API)."""
    logger.info("protect_delete_liveview called for %s (confirm=%s)", liveview_id, confirm)
    try:
        result = await liveview_manager.delete_liveview(liveview_id)
        return {"success": False, "error": result["message"], "data": result}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error("Error deleting liveview %s: %s", liveview_id, e, exc_info=True)
        return {"success": False, "error": f"Failed to delete liveview: {e}"}


logger.info(
    "Liveview tools registered: protect_list_liveviews, protect_create_liveview, protect_delete_liveview"
)
