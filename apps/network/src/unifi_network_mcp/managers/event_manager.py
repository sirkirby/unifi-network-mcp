"""Event Manager for UniFi Network MCP server.

Manages event log and alarm operations for viewing system events and alerts.
"""

import logging
from typing import Any, Dict, List, Optional

from aiounifi.models.api import ApiRequest

from .connection_manager import ConnectionManager

logger = logging.getLogger("unifi-network-mcp")


class EventManager:
    """Manages event log operations on the UniFi Controller."""

    def __init__(self, connection_manager: ConnectionManager):
        """Initialize the Event Manager.

        Args:
            connection_manager: The shared ConnectionManager instance.
        """
        self._connection = connection_manager

    async def get_events(
        self,
        within: int = 24,
        limit: int = 100,
        start: int = 0,
        event_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get events from the controller.

        Events are retrieved via POST to /stat/event with filter parameters.

        Args:
            within: Hours to look back (default 24).
            limit: Maximum number of events to return (default 100, max 3000).
            start: Offset for pagination (default 0).
            event_type: Optional filter for specific event type prefix (e.g., 'EVT_SW_').

        Returns:
            List of event objects containing timestamp, message, and event details.
        """
        # Events are time-sensitive, skip caching
        try:
            payload: Dict[str, Any] = {
                "within": within,
                "_limit": min(limit, 3000),  # API max is 3000
                "_start": start,
            }

            if event_type:
                payload["type"] = event_type

            api_request = ApiRequest(
                method="post",
                path="/stat/event",
                data=payload,
            )
            response = await self._connection.request(api_request)

            events = (
                response
                if isinstance(response, list)
                else response.get("data", [])
                if isinstance(response, dict)
                else []
            )

            return events
        except Exception as e:
            logger.error(f"Error getting events: {e}")
            return []

    async def get_alarms(
        self,
        archived: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get active alarms/alerts from the controller.

        Alarms are retrieved via GET to /stat/alarm.

        Args:
            archived: Include archived alarms (default False).
            limit: Maximum number of alarms to return (default 100).

        Returns:
            List of alarm objects containing severity, message, and timestamp.
        """
        try:
            path = "/stat/alarm"
            if archived:
                path = "/stat/alarm?archived=true"

            api_request = ApiRequest(method="get", path=path)
            response = await self._connection.request(api_request)

            alarms = (
                response
                if isinstance(response, list)
                else response.get("data", [])
                if isinstance(response, dict)
                else []
            )

            return alarms[:limit]
        except Exception as e:
            logger.error(f"Error getting alarms: {e}")
            return []

    def get_event_type_prefixes(self) -> List[Dict[str, str]]:
        """Get a list of known event type prefixes for filtering.

        Returns:
            List of dicts with prefix and description for common event types.
        """
        return [
            {"prefix": "EVT_SW_", "description": "Switch events"},
            {"prefix": "EVT_AP_", "description": "Access Point events"},
            {"prefix": "EVT_GW_", "description": "Gateway events"},
            {"prefix": "EVT_LAN_", "description": "LAN events"},
            {
                "prefix": "EVT_WU_",
                "description": "WLAN User events (connect/disconnect)",
            },
            {"prefix": "EVT_WG_", "description": "WLAN Guest events"},
            {"prefix": "EVT_IPS_", "description": "IPS/IDS security events"},
            {"prefix": "EVT_AD_", "description": "Admin events"},
            {"prefix": "EVT_DPI_", "description": "Deep Packet Inspection events"},
        ]

    async def archive_alarm(self, alarm_id: str) -> bool:
        """Archive an alarm (mark as resolved).

        Uses POST to /cmd/evtmgr with archive-alarm command.

        Args:
            alarm_id: The _id of the alarm to archive.

        Returns:
            True if successful, False otherwise.
        """
        try:
            api_request = ApiRequest(
                method="post",
                path="/cmd/evtmgr",
                data={
                    "cmd": "archive-alarm",
                    "_id": alarm_id,
                },
            )
            await self._connection.request(api_request)
            logger.info(f"Archived alarm {alarm_id}")
            return True
        except Exception as e:
            logger.error(f"Error archiving alarm {alarm_id}: {e}")
            return False

    async def archive_all_alarms(self) -> bool:
        """Archive all active alarms.

        Uses POST to /cmd/evtmgr with archive-all-alarms command.

        Returns:
            True if successful, False otherwise.
        """
        try:
            api_request = ApiRequest(
                method="post",
                path="/cmd/evtmgr",
                data={"cmd": "archive-all-alarms"},
            )
            await self._connection.request(api_request)
            logger.info("Archived all alarms")
            return True
        except Exception as e:
            logger.error(f"Error archiving all alarms: {e}")
            return False
