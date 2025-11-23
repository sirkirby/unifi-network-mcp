"""Event log tools for UniFi Network MCP server.

Provides MCP tools for viewing events and alarms from the UniFi controller.
Events include system logs, client connections, device status changes, and more.
"""

import logging
import json
from typing import Dict, Any, Optional, List

from src.runtime import server, config
from src.utils.permissions import parse_permission

logger = logging.getLogger(__name__)


def _get_event_manager():
    """Lazy import to avoid circular dependency."""
    from src.runtime import event_manager
    return event_manager


@server.tool(
    name="unifi_list_events",
    description="List recent events from the UniFi controller with optional filtering.",
)
async def list_events(
    within: int = 24,
    limit: int = 100,
    event_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Lists events from the UniFi controller.

    Events include client connections/disconnections, device status changes,
    firmware updates, security alerts, and more.

    Args:
        within (int, optional): Hours to look back (default 24).
        limit (int, optional): Maximum events to return (default 100, max 3000).
        event_type (str, optional): Filter by event type prefix (e.g., 'EVT_SW_').
            Common prefixes:
            - EVT_SW_* - Switch events
            - EVT_AP_* - Access Point events
            - EVT_GW_* - Gateway events
            - EVT_LAN_* - LAN events
            - EVT_WU_* - WLAN User events (client connect/disconnect)
            - EVT_IPS_* - IPS/IDS events

    Returns:
        A dictionary containing:
        - success (bool): Indicates if the operation was successful.
        - site (str): The identifier of the UniFi site queried.
        - count (int): The number of events returned.
        - events (List[Dict]): A list of events with:
            - id (str): Event ID.
            - type (str): Event type (e.g., 'EVT_WU_Connected').
            - time (str): Event timestamp.
            - message (str): Human-readable event message.
            - key (str): Event key.
            - subsystem (str): Subsystem that generated the event.
        - error (str, optional): An error message if the operation failed.

    Example response:
    {
        "success": True,
        "site": "default",
        "count": 50,
        "events": [
            {
                "id": "60d4e5f6a7b8c9d0e1f2a3b4",
                "type": "EVT_WU_Connected",
                "time": "2025-01-15T10:30:00Z",
                "message": "User[aa:bb:cc:dd:ee:ff] has connected to AP[...]",
                "key": "EVT_WU_Connected",
                "subsystem": "wlan"
            }
        ]
    }
    """
    if not parse_permission(config.permissions, "event", "read"):
        logger.warning("Permission denied for listing events.")
        return {"success": False, "error": "Permission denied to list events."}

    try:
        event_manager = _get_event_manager()
        events = await event_manager.get_events(
            within=within,
            limit=limit,
            event_type=event_type,
        )

        formatted_events = []
        for e in events:
            formatted_events.append({
                "id": e.get("_id"),
                "type": e.get("key", e.get("type", "unknown")),
                "time": e.get("time") or e.get("datetime"),
                "message": e.get("msg", e.get("message", "")),
                "key": e.get("key"),
                "subsystem": e.get("subsystem", "unknown"),
                "user": e.get("user"),
                "hostname": e.get("hostname"),
                "ap": e.get("ap"),
                "ssid": e.get("ssid"),
            })

        return {
            "success": True,
            "site": event_manager._connection.site,
            "count": len(formatted_events),
            "within_hours": within,
            "filter": event_type,
            "events": formatted_events,
        }
    except Exception as e:
        logger.error(f"Error listing events: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_list_alarms",
    description="List active alarms/alerts from the UniFi controller.",
)
async def list_alarms(
    include_archived: bool = False,
    limit: int = 100,
) -> Dict[str, Any]:
    """Lists alarms from the UniFi controller.

    Alarms are important alerts that require attention, such as device
    disconnections, high CPU usage, or security threats.

    Args:
        include_archived (bool, optional): Include archived/resolved alarms (default False).
        limit (int, optional): Maximum alarms to return (default 100).

    Returns:
        A dictionary containing:
        - success (bool): Indicates if the operation was successful.
        - site (str): The identifier of the UniFi site queried.
        - count (int): The number of alarms found.
        - alarms (List[Dict]): A list of alarms with details.
        - error (str, optional): An error message if the operation failed.
    """
    if not parse_permission(config.permissions, "event", "read"):
        logger.warning("Permission denied for listing alarms.")
        return {"success": False, "error": "Permission denied to list alarms."}

    try:
        event_manager = _get_event_manager()
        alarms = await event_manager.get_alarms(
            archived=include_archived,
            limit=limit,
        )

        formatted_alarms = []
        for a in alarms:
            formatted_alarms.append({
                "id": a.get("_id"),
                "type": a.get("key", a.get("type", "unknown")),
                "time": a.get("time") or a.get("datetime"),
                "message": a.get("msg", a.get("message", "")),
                "archived": a.get("archived", False),
                "handled_admin_id": a.get("handled_admin_id"),
                "handled_time": a.get("handled_time"),
            })

        return {
            "success": True,
            "site": event_manager._connection.site,
            "count": len(formatted_alarms),
            "include_archived": include_archived,
            "alarms": formatted_alarms,
        }
    except Exception as e:
        logger.error(f"Error listing alarms: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_get_event_types",
    description="Get a list of common event type prefixes for filtering events.",
)
async def get_event_types() -> Dict[str, Any]:
    """Gets a list of common event type prefixes.

    Use these prefixes with unifi_list_events to filter for specific event types.

    Returns:
        A dictionary containing:
        - success (bool): Indicates if the operation was successful.
        - event_types (List[Dict]): Event type prefixes with descriptions.
    """
    if not parse_permission(config.permissions, "event", "read"):
        logger.warning("Permission denied for getting event types.")
        return {"success": False, "error": "Permission denied."}

    event_types = [
        {"prefix": "EVT_SW_", "description": "Switch events (port changes, PoE, etc.)"},
        {"prefix": "EVT_AP_", "description": "Access Point events (status, channel changes)"},
        {"prefix": "EVT_GW_", "description": "Gateway/Router events (WAN, routing)"},
        {"prefix": "EVT_LAN_", "description": "LAN events (DHCP, network changes)"},
        {"prefix": "EVT_WU_", "description": "WLAN User events (client connect/disconnect)"},
        {"prefix": "EVT_WG_", "description": "WLAN Guest events (guest portal)"},
        {"prefix": "EVT_IPS_", "description": "IPS/IDS security events"},
        {"prefix": "EVT_AD_", "description": "Admin events (login, config changes)"},
        {"prefix": "EVT_DPI_", "description": "Deep Packet Inspection events"},
    ]

    return {
        "success": True,
        "event_types": event_types,
        "usage_hint": "Use these prefixes with the 'event_type' parameter in unifi_list_events",
    }


@server.tool(
    name="unifi_archive_alarm",
    description="Archive (acknowledge/resolve) an alarm. Requires confirmation.",
    permission_category="events",
    permission_action="update",
)
async def archive_alarm(
    alarm_id: str,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Archives an alarm, marking it as resolved/acknowledged.

    Args:
        alarm_id (str): The unique identifier (_id) of the alarm to archive.
        confirm (bool): Must be True to execute. Defaults to False.

    Returns:
        A dictionary containing:
        - success (bool): Whether the operation succeeded.
        - alarm_id (str): The ID of the archived alarm.
        - message (str): Confirmation message.
        - error (str, optional): Error message if failed.
    """
    if not parse_permission(config.permissions, "event", "update"):
        logger.warning("Permission denied for archiving alarm.")
        return {"success": False, "error": "Permission denied to archive alarm."}

    if not alarm_id:
        return {"success": False, "error": "alarm_id is required"}

    if not confirm:
        return {
            "success": False,
            "error": "Confirmation required. Set 'confirm' to true.",
            "preview": {"alarm_id": alarm_id, "action": "archive"},
        }

    try:
        event_manager = _get_event_manager()
        success = await event_manager.archive_alarm(alarm_id)

        if success:
            return {
                "success": True,
                "alarm_id": alarm_id,
                "message": f"Alarm '{alarm_id}' archived successfully.",
            }
        else:
            return {
                "success": False,
                "error": f"Failed to archive alarm {alarm_id}. Check server logs.",
            }
    except Exception as e:
        logger.error(f"Error archiving alarm {alarm_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_archive_all_alarms",
    description="Archive all active alarms at once. Requires confirmation.",
    permission_category="events",
    permission_action="update",
)
async def archive_all_alarms(
    confirm: bool = False,
) -> Dict[str, Any]:
    """Archives all active alarms, marking them as resolved.

    Args:
        confirm (bool): Must be True to execute. Defaults to False.

    Returns:
        A dictionary containing:
        - success (bool): Whether the operation succeeded.
        - message (str): Confirmation message.
        - error (str, optional): Error message if failed.
    """
    if not parse_permission(config.permissions, "event", "update"):
        logger.warning("Permission denied for archiving all alarms.")
        return {"success": False, "error": "Permission denied to archive alarms."}

    if not confirm:
        return {
            "success": False,
            "error": "Confirmation required. Set 'confirm' to true.",
            "preview": {"action": "archive_all_alarms"},
            "warning": "This will archive ALL active alarms.",
        }

    try:
        event_manager = _get_event_manager()
        success = await event_manager.archive_all_alarms()

        if success:
            return {
                "success": True,
                "message": "All alarms archived successfully.",
            }
        else:
            return {
                "success": False,
                "error": "Failed to archive all alarms. Check server logs.",
            }
    except Exception as e:
        logger.error(f"Error archiving all alarms: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
