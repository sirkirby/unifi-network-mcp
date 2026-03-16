"""
UniFi Network MCP event and alarm tools.

This module provides MCP tools to view events and manage alarms on a UniFi Network Controller.
"""

import logging
from typing import Any, Dict, Optional

from src.runtime import config, server
from src.utils.confirmation import should_auto_confirm
from src.utils.permissions import parse_permission

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependencies
_event_manager = None


def _get_event_manager():
    """Lazy-load the event manager to avoid circular imports."""
    global _event_manager
    if _event_manager is None:
        from src.managers.event_manager import EventManager
        from src.runtime import get_connection_manager

        _event_manager = EventManager(get_connection_manager())
    return _event_manager


@server.tool(
    name="unifi_list_events",
    description=(
        "Returns timestamped event log entries (client connects/disconnects, device "
        "state changes, firmware updates, config changes) sorted newest-first. "
        "Filter by within_hours (default 24), event_type prefix (use unifi_get_event_types "
        "for valid prefixes), and paginate with start/limit. "
        "For critical alerts specifically, use unifi_list_alarms instead."
    ),
)
async def list_events(
    within_hours: int = 24,
    limit: int = 100,
    start: int = 0,
    event_type: Optional[str] = None,
) -> Dict[str, Any]:
    """List events with optional filtering."""
    try:
        event_manager = _get_event_manager()
        events = await event_manager.get_events(
            within=within_hours,
            limit=limit,
            start=start,
            event_type=event_type,
        )

        return {
            "success": True,
            "site": event_manager._connection.site,
            "count": len(events),
            "filters": {
                "within_hours": within_hours,
                "limit": limit,
                "start": start,
                "event_type": event_type,
            },
            "events": events,
        }
    except Exception as e:
        logger.error(f"Error listing events: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_list_alarms",
    description=(
        "Returns active alarms (security alerts, connectivity issues, firmware warnings). "
        "Each alarm includes type, message, timestamp, and related device/client MAC. "
        "By default shows only unresolved alarms; set include_archived=true for history. "
        "For general event logs (non-critical), use unifi_list_events."
    ),
)
async def list_alarms(
    include_archived: bool = False,
    limit: int = 100,
) -> Dict[str, Any]:
    """List alarms with optional archived filter."""
    try:
        event_manager = _get_event_manager()
        alarms = await event_manager.get_alarms(
            archived=include_archived,
            limit=limit,
        )

        return {
            "success": True,
            "site": event_manager._connection.site,
            "count": len(alarms),
            "include_archived": include_archived,
            "alarms": alarms,
        }
    except Exception as e:
        logger.error(f"Error listing alarms: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_get_event_types",
    description="""Get a list of known event type prefixes for filtering events.

Use these prefixes with unifi_list_events event_type parameter to filter specific event categories.""",
)
async def get_event_types() -> Dict[str, Any]:
    """Get list of event type prefixes."""
    try:
        event_manager = _get_event_manager()
        prefixes = event_manager.get_event_type_prefixes()

        return {
            "success": True,
            "event_types": prefixes,
            "usage": "Use prefix value with unifi_list_events event_type parameter",
        }
    except Exception as e:
        logger.error(f"Error getting event types: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_archive_alarm",
    description="Archive (resolve/dismiss) a specific alarm by its ID",
    permission_category="events",
    permission_action="update",
)
async def archive_alarm(alarm_id: str, confirm: bool = False) -> Dict[str, Any]:
    """Archive a specific alarm."""
    if not parse_permission(config.permissions, "event", "update"):
        logger.warning(f"Permission denied for archiving alarm ({alarm_id}).")
        return {"success": False, "error": "Permission denied to archive alarms."}

    if not confirm and not should_auto_confirm():
        return {"success": False, "error": "Confirmation required. Set confirm=true."}

    try:
        event_manager = _get_event_manager()
        success = await event_manager.archive_alarm(alarm_id)

        if success:
            return {
                "success": True,
                "message": f"Alarm {alarm_id} archived successfully.",
            }
        return {"success": False, "error": f"Failed to archive alarm {alarm_id}."}
    except Exception as e:
        logger.error(f"Error archiving alarm {alarm_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_archive_all_alarms",
    description="Archive (resolve/dismiss) all active alarms",
    permission_category="events",
    permission_action="update",
)
async def archive_all_alarms(confirm: bool = False) -> Dict[str, Any]:
    """Archive all active alarms."""
    if not parse_permission(config.permissions, "event", "update"):
        logger.warning("Permission denied for archiving all alarms.")
        return {"success": False, "error": "Permission denied to archive alarms."}

    if not confirm and not should_auto_confirm():
        return {"success": False, "error": "Confirmation required. Set confirm=true."}

    try:
        event_manager = _get_event_manager()
        success = await event_manager.archive_all_alarms()

        if success:
            return {
                "success": True,
                "message": "All alarms archived successfully.",
            }
        return {"success": False, "error": "Failed to archive all alarms."}
    except Exception as e:
        logger.error(f"Error archiving all alarms: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
