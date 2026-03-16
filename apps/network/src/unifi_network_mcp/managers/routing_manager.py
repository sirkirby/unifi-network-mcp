"""Routing Manager for UniFi Network MCP server.

Manages static route operations for advanced routing configuration.
"""

import logging
from typing import Any, Dict, List, Optional

from aiounifi.models.api import ApiRequest

from .connection_manager import ConnectionManager

logger = logging.getLogger("unifi-network-mcp")

CACHE_PREFIX_ROUTES = "routes"


class RoutingManager:
    """Manages static route operations on the UniFi Controller."""

    def __init__(self, connection_manager: ConnectionManager):
        """Initialize the Routing Manager.

        Args:
            connection_manager: The shared ConnectionManager instance.
        """
        self._connection = connection_manager

    async def get_routes(self) -> List[Dict[str, Any]]:
        """Get all user-defined static routes for the current site.

        Uses GET /rest/routing endpoint.

        Returns:
            List of route objects containing network, nexthop, and settings.
        """
        cache_key = f"{CACHE_PREFIX_ROUTES}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            api_request = ApiRequest(method="get", path="/rest/routing")
            response = await self._connection.request(api_request)

            routes = (
                response
                if isinstance(response, list)
                else response.get("data", [])
                if isinstance(response, dict)
                else []
            )

            self._connection._update_cache(cache_key, routes)
            return routes
        except Exception as e:
            logger.error(f"Error getting routes: {e}")
            return []

    async def get_active_routes(self) -> List[Dict[str, Any]]:
        """Get all active routes (including system routes) from the device.

        Note: This uses an undocumented /stat/routing endpoint that may not
        be available on all controller versions. Falls back gracefully to
        returning an empty list if the endpoint doesn't exist.

        Returns:
            List of active route objects from the routing table, or empty
            list if the endpoint is unavailable.
        """
        try:
            api_request = ApiRequest(method="get", path="/stat/routing")
            response = await self._connection.request(api_request)

            routes = (
                response
                if isinstance(response, list)
                else response.get("data", [])
                if isinstance(response, dict)
                else []
            )

            return routes
        except Exception as e:
            # This endpoint may not exist on all controllers
            if "404" in str(e) or "Not Found" in str(e):
                logger.debug("Active routes endpoint /stat/routing not available on this controller")
            else:
                logger.error(f"Error getting active routes: {e}")
            return []

    async def get_route_details(self, route_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific route by ID.

        Args:
            route_id: The _id of the route.

        Returns:
            Route object or None if not found.
        """
        try:
            all_routes = await self.get_routes()
            route = next((r for r in all_routes if r.get("_id") == route_id), None)
            if not route:
                logger.debug(f"Route {route_id} not found.")
            return route
        except Exception as e:
            logger.error(f"Error getting route details for {route_id}: {e}")
            return None

    async def create_route(
        self,
        name: str,
        static_route_network: str,
        static_route_nexthop: str,
        static_route_distance: int = 1,
        enabled: bool = True,
        route_type: str = "nexthop-route",
    ) -> Optional[Dict[str, Any]]:
        """Create a new static route.

        Uses POST to /rest/routing endpoint.

        Args:
            name: Name/description for the route.
            static_route_network: Destination network in CIDR format (e.g., "10.0.0.0/24").
            static_route_nexthop: Next-hop IP address or interface.
            static_route_distance: Administrative distance (default 1).
            enabled: Whether the route is enabled (default True).
            route_type: Route type (default "nexthop-route").

        Returns:
            Created route object, or None on failure.
        """
        try:
            payload: Dict[str, Any] = {
                "name": name,
                "static-route_network": static_route_network,
                "static-route_nexthop": static_route_nexthop,
                "static-route_distance": static_route_distance,
                "enabled": enabled,
                "type": route_type,
            }

            api_request = ApiRequest(
                method="post",
                path="/rest/routing",
                data=payload,
            )
            response = await self._connection.request(api_request)

            logger.info(f"Created route: {name} -> {static_route_network} via {static_route_nexthop}")

            # Invalidate cache
            self._connection._invalidate_cache(f"{CACHE_PREFIX_ROUTES}_{self._connection.site}")

            # Return the created route
            if isinstance(response, list) and len(response) > 0:
                return response[0]
            elif isinstance(response, dict):
                return response.get("data", [response])[0] if response else None

            return None

        except Exception as e:
            logger.error(f"Error creating route: {e}", exc_info=True)
            return None

    async def update_route(
        self,
        route_id: str,
        name: Optional[str] = None,
        static_route_network: Optional[str] = None,
        static_route_nexthop: Optional[str] = None,
        static_route_distance: Optional[int] = None,
        enabled: Optional[bool] = None,
    ) -> bool:
        """Update an existing static route.

        Uses PUT to /rest/routing/{route_id} endpoint.
        Sends the full merged object (not partial updates) as required by the API.

        Args:
            route_id: The _id of the route to update.
            name: Optional new name for the route.
            static_route_network: Optional new destination network.
            static_route_nexthop: Optional new next-hop address.
            static_route_distance: Optional new administrative distance.
            enabled: Optional enable/disable setting.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Get current route data first
            current = await self.get_route_details(route_id)
            if not current:
                logger.error(f"Route {route_id} not found for update.")
                return False

            # Start with the full existing route and apply updates
            payload: Dict[str, Any] = current.copy()

            # Apply updates to the full object
            if name is not None:
                payload["name"] = name
            if static_route_network is not None:
                payload["static-route_network"] = static_route_network
            if static_route_nexthop is not None:
                payload["static-route_nexthop"] = static_route_nexthop
            if static_route_distance is not None:
                payload["static-route_distance"] = static_route_distance
            if enabled is not None:
                payload["enabled"] = enabled

            api_request = ApiRequest(
                method="put",
                path=f"/rest/routing/{route_id}",
                data=payload,
            )
            await self._connection.request(api_request)

            logger.info(f"Updated route {route_id}")

            # Invalidate cache
            self._connection._invalidate_cache(f"{CACHE_PREFIX_ROUTES}_{self._connection.site}")

            return True

        except Exception as e:
            logger.error(f"Error updating route {route_id}: {e}", exc_info=True)
            return False
