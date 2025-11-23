"""Event Manager for UniFi Network MCP server.

Manages event log operations for viewing system events and alerts.
"""

import logging
from typing import Dict, List, Optional, Any

from aiounifi.models.api import ApiRequest
from .connection_manager import ConnectionManager

logger = logging.getLogger("unifi-network-mcp")

CACHE_PREFIX_EVENTS = "events"


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

        Args:
            within: Hours to look back (default 24).
            limit: Maximum number of events to return (default 100, max 3000).
            start: Offset for pagination (default 0).
            event_type: Optional filter for specific event type (e.g., 'EVT_SW_*').

        Returns:
            List of event objects.
        """
        # Events are time-sensitive, so we use a shorter cache or no cache
        # For now, we skip caching for events as they change frequently
        try:
            payload: Dict[str, Any] = {
                "within": within,
                "_limit": min(limit, 3000),  # API max is 3000
                "_start": start,
            }

            # Add type filter if specified
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

        Args:
            archived: Include archived alarms (default False).
            limit: Maximum number of alarms to return (default 100).

        Returns:
            List of alarm objects.
        """
        try:
            api_request = ApiRequest(
                method="get",
                path="/stat/alarm" if not archived else "/stat/alarm?archived=true",
            )
            response = await self._connection.request(api_request)

            alarms = (
                response
                if isinstance(response, list)
                else response.get("data", [])
                if isinstance(response, dict)
                else []
            )

            # Apply limit
            return alarms[:limit]
        except Exception as e:
            logger.error(f"Error getting alarms: {e}")
            return []

    async def get_event_types(self) -> List[str]:
        """Get a list of common event types.

        This returns a static list of known event type prefixes that can be
        used for filtering.

        Returns:
            List of event type prefixes.
        """
        return [
            "EVT_SW_",  # Switch events
            "EVT_AP_",  # Access Point events
            "EVT_GW_",  # Gateway events
            "EVT_LAN_",  # LAN events
            "EVT_WU_",  # WLAN User events (client connect/disconnect)
            "EVT_WG_",  # WLAN Guest events
            "EVT_IPS_",  # IPS/IDS events
            "EVT_AD_",  # Admin events
            "EVT_DPI_",  # Deep Packet Inspection events
        ]

    async def archive_alarm(self, alarm_id: str) -> bool:
        """Archive an alarm (mark as resolved).

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
