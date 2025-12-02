"""Traffic Route Manager for UniFi Network MCP server.

Manages policy-based traffic routing (V2 API) for VPN routing,
domain-based routing, and other advanced routing scenarios.
"""

import logging
from typing import Any, Dict, List, Optional

from aiounifi.models.api import ApiRequestV2

from .connection_manager import ConnectionManager

logger = logging.getLogger("unifi-network-mcp")

CACHE_PREFIX_TRAFFIC_ROUTES = "traffic_routes"


class TrafficRouteManager:
    """Manages traffic route operations on the UniFi Controller.

    Traffic routes are policy-based routing rules that can route traffic
    based on domains, IP addresses, regions, or target devices through
    specific networks (like VPNs).
    """

    def __init__(self, connection_manager: ConnectionManager):
        """Initialize the Traffic Route Manager.

        Args:
            connection_manager: The shared ConnectionManager instance.
        """
        self._connection = connection_manager

    async def get_traffic_routes(self) -> List[Dict[str, Any]]:
        """Get all traffic routes for the current site.

        Uses GET /trafficroutes endpoint (V2 API).

        Returns:
            List of traffic route objects.
        """
        cache_key = f"{CACHE_PREFIX_TRAFFIC_ROUTES}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            api_request = ApiRequestV2(method="get", path="/trafficroutes", data=None)
            response = await self._connection.request(api_request)

            routes = (
                response.get("data", [])
                if isinstance(response, dict)
                else response
                if isinstance(response, list)
                else []
            )

            self._connection._update_cache(cache_key, routes)
            return routes
        except Exception as e:
            logger.error(f"Error getting traffic routes: {e}")
            return []

    async def get_traffic_route_details(self, route_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific traffic route by ID.

        Args:
            route_id: The _id of the traffic route.

        Returns:
            Traffic route object or None if not found.
        """
        try:
            all_routes = await self.get_traffic_routes()
            route = next((r for r in all_routes if r.get("_id") == route_id), None)
            if not route:
                logger.debug(f"Traffic route {route_id} not found.")
            return route
        except Exception as e:
            logger.error(f"Error getting traffic route details for {route_id}: {e}")
            return None

    async def update_traffic_route(self, route_id: str, enabled: Optional[bool] = None, **kwargs) -> bool:
        """Update a traffic route.

        Uses PUT /trafficroutes/{route_id} endpoint (V2 API).
        Sends the full merged object as required by the API.

        Args:
            route_id: The _id of the traffic route to update.
            enabled: Optional enable/disable setting.
            **kwargs: Additional fields to update.

        Returns:
            True if successful, False otherwise.
        """
        try:
            current = await self.get_traffic_route_details(route_id)
            if not current:
                logger.error(f"Traffic route {route_id} not found for update.")
                return False

            # Start with full existing route and apply updates
            payload: Dict[str, Any] = current.copy()

            if enabled is not None:
                payload["enabled"] = enabled

            # Apply any additional updates
            for key, value in kwargs.items():
                if value is not None:
                    payload[key] = value

            api_request = ApiRequestV2(
                method="put",
                path=f"/trafficroutes/{route_id}",
                data=payload,
            )
            await self._connection.request(api_request)

            logger.info(f"Updated traffic route {route_id}")

            # Invalidate cache
            self._connection._invalidate_cache(f"{CACHE_PREFIX_TRAFFIC_ROUTES}_{self._connection.site}")

            return True

        except Exception as e:
            logger.error(f"Error updating traffic route {route_id}: {e}", exc_info=True)
            return False

    async def toggle_traffic_route(self, route_id: str) -> bool:
        """Toggle a traffic route's enabled state.

        Args:
            route_id: The _id of the traffic route to toggle.

        Returns:
            True if successful, False otherwise.
        """
        current = await self.get_traffic_route_details(route_id)
        if not current:
            logger.error(f"Traffic route {route_id} not found for toggle.")
            return False

        new_state = not current.get("enabled", True)
        return await self.update_traffic_route(route_id, enabled=new_state)

    async def update_kill_switch(self, route_id: str, enabled: bool) -> bool:
        """Update the kill switch setting for a traffic route.

        The kill switch blocks all traffic if the route's target network
        (e.g., VPN) becomes unavailable.

        Args:
            route_id: The _id of the traffic route.
            enabled: Whether to enable or disable the kill switch.

        Returns:
            True if successful, False otherwise.
        """
        try:
            current = await self.get_traffic_route_details(route_id)
            if not current:
                logger.error(f"Traffic route {route_id} not found for kill switch update.")
                return False

            payload: Dict[str, Any] = current.copy()
            payload["kill_switch_enabled"] = enabled

            api_request = ApiRequestV2(
                method="put",
                path=f"/trafficroutes/{route_id}",
                data=payload,
            )
            await self._connection.request(api_request)

            logger.info(f"Traffic route {route_id} kill switch {'enabled' if enabled else 'disabled'}")

            self._connection._invalidate_cache(f"{CACHE_PREFIX_TRAFFIC_ROUTES}_{self._connection.site}")

            return True

        except Exception as e:
            logger.error(
                f"Error updating kill switch for traffic route {route_id}: {e}",
                exc_info=True,
            )
            return False
