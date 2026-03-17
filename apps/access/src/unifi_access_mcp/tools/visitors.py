"""Visitor tools for UniFi Access MCP server.

Provides tools for listing and inspecting visitor passes.
"""

import logging
from typing import Any, Dict

from mcp.types import ToolAnnotations

from unifi_access_mcp.runtime import server, visitor_manager

logger = logging.getLogger(__name__)


@server.tool(
    name="access_list_visitors",
    description=(
        "Lists all visitor passes with their name, status, "
        "valid time range, and assigned doors."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def access_list_visitors() -> Dict[str, Any]:
    """List all visitors."""
    logger.info("access_list_visitors tool called")
    try:
        visitors = await visitor_manager.list_visitors()
        return {"success": True, "data": {"visitors": visitors, "count": len(visitors)}}
    except NotImplementedError:
        return {"success": False, "error": "Visitor listing not yet implemented"}
    except Exception as e:
        logger.error("Error listing visitors: %s", e, exc_info=True)
        return {"success": False, "error": f"Failed to list visitors: {e}"}


@server.tool(
    name="access_get_visitor",
    description="Returns detailed information for a single visitor pass.",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def access_get_visitor(visitor_id: str) -> Dict[str, Any]:
    """Get detailed visitor information by ID."""
    logger.info("access_get_visitor tool called for %s", visitor_id)
    try:
        detail = await visitor_manager.get_visitor(visitor_id)
        return {"success": True, "data": detail}
    except NotImplementedError:
        return {"success": False, "error": "Visitor detail not yet implemented"}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error("Error getting visitor %s: %s", visitor_id, e, exc_info=True)
        return {"success": False, "error": f"Failed to get visitor: {e}"}


logger.info("Visitor tools registered: access_list_visitors, access_get_visitor")
