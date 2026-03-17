"""Event tools for UniFi Access MCP server.

Provides tools for querying access events (door opens, denials, etc.)
from the Access controller.
"""

import logging
from typing import Any, Dict

from mcp.types import ToolAnnotations

from unifi_access_mcp.runtime import event_manager, server

logger = logging.getLogger(__name__)


@server.tool(
    name="access_list_events",
    description=(
        "Query access events from the controller with optional filters. "
        "Returns events such as door unlocks, access denials, and system events."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def access_list_events() -> Dict[str, Any]:
    """List access events."""
    logger.info("access_list_events tool called")
    try:
        events = await event_manager.list_events()
        return {"success": True, "data": {"events": events, "count": len(events)}}
    except NotImplementedError:
        return {"success": False, "error": "Event listing not yet implemented"}
    except Exception as e:
        logger.error("Error listing events: %s", e, exc_info=True)
        return {"success": False, "error": f"Failed to list events: {e}"}


@server.tool(
    name="access_get_event",
    description="Returns detailed information for a single access event.",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def access_get_event(event_id: str) -> Dict[str, Any]:
    """Get a single event by ID."""
    logger.info("access_get_event tool called for %s", event_id)
    try:
        event = await event_manager.get_event(event_id)
        return {"success": True, "data": event}
    except NotImplementedError:
        return {"success": False, "error": "Event detail not yet implemented"}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error("Error getting event %s: %s", event_id, e, exc_info=True)
        return {"success": False, "error": f"Failed to get event: {e}"}


@server.tool(
    name="access_recent_events",
    description=(
        "Get recent events from the in-memory buffer. Fast (no API call). "
        "Use for real-time monitoring; use access_list_events for historical queries."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def access_recent_events() -> Dict[str, Any]:
    """Get recent events from the websocket buffer."""
    logger.info("access_recent_events called")
    try:
        events = event_manager.get_recent_from_buffer()
        return {
            "success": True,
            "data": {
                "events": events,
                "count": len(events),
                "source": "websocket_buffer",
                "buffer_size": event_manager.buffer_size,
            },
        }
    except Exception as e:
        logger.error("Error reading recent events: %s", e, exc_info=True)
        return {"success": False, "error": f"Failed to read recent events: {e}"}


logger.info("Event tools registered: access_list_events, access_get_event, access_recent_events")
