"""Routing Manager for UniFi Network MCP server.

Manages static route operations for advanced routing configuration.
"""

import logging
from typing import Dict, List, Optional, Any

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
        """Get all static routes for the current site.

        Returns:
            List of static route objects.
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
            logger.error(f"Error getting static routes: {e}")
            return []

    async def get_route_details(self, route_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific static route by ID.

        Args:
            route_id: The _id of the static route.

        Returns:
            Route object or None if not found.
        """
        try:
            all_routes = await self.get_routes()
            route = next(
                (r for r in all_routes if r.get("_id") == route_id), None
            )
            if not route:
                logger.debug(f"Static route {route_id} not found.")
            return route
        except Exception as e:
            logger.error(f"Error getting route details for {route_id}: {e}")
            return None

    async def get_route_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a static route by its name.

        Args:
            name: The name of the static route.

        Returns:
            Route object or None if not found.
        """
        try:
            all_routes = await self.get_routes()
            route = next(
                (r for r in all_routes if r.get("name") == name), None
            )
            return route
        except Exception as e:
            logger.error(f"Error getting route by name '{name}': {e}")
            return None

    async def create_route(
        self,
        name: str,
        static_route_network: str,
        static_route_nexthop: str,
        static_route_distance: int = 1,
        enabled: bool = True,
        static_route_type: str = "nexthop-route",
    ) -> Optional[Dict[str, Any]]:
        """Create a new static route.

        Args:
            name: Name of the route.
            static_route_network: Target network in CIDR notation (e.g., '10.0.0.0/8').
            static_route_nexthop: Next-hop IP address or interface.
            static_route_distance: Administrative distance (default 1).
            enabled: Whether the route is enabled (default True).
            static_route_type: Route type (default 'nexthop-route').

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
                "type": static_route_type,
            }

            api_request = ApiRequest(
                method="post",
                path="/rest/routing",
                data=payload,
            )
            response = await self._connection.request(api_request)

            logger.info(f"Create static route command sent: '{name}'")

            # Invalidate cache
            self._connection._invalidate_cache(
                f"{CACHE_PREFIX_ROUTES}_{self._connection.site}"
            )

            # Extract created route from response
            if isinstance(response, list) and len(response) > 0:
                return response[0]
            elif isinstance(response, dict):
                if "data" in response and isinstance(response["data"], list):
                    return response["data"][0] if response["data"] else None
                return response

            return None

        except Exception as e:
            logger.error(f"Error creating static route '{name}': {e}", exc_info=True)
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

        Args:
            route_id: The _id of the static route to update.
            name: New name for the route (optional).
            static_route_network: New target network (optional).
            static_route_nexthop: New next-hop (optional).
            static_route_distance: New administrative distance (optional).
            enabled: Enable/disable route (optional).

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Fetch existing route
            existing = await self.get_route_details(route_id)
            if not existing:
                logger.error(f"Static route {route_id} not found for update.")
                return False

            # Build update payload - merge with existing
            payload = existing.copy()

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

            logger.info(f"Update static route command sent for {route_id}")

            # Invalidate cache
            self._connection._invalidate_cache(
                f"{CACHE_PREFIX_ROUTES}_{self._connection.site}"
            )

            return True

        except Exception as e:
            logger.error(f"Error updating static route {route_id}: {e}", exc_info=True)
            return False

    async def delete_route(self, route_id: str) -> bool:
        """Delete a static route.

        Args:
            route_id: The _id of the static route to delete.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Verify it exists first
            existing = await self.get_route_details(route_id)
            if not existing:
                logger.error(f"Static route {route_id} not found for deletion.")
                return False

            api_request = ApiRequest(
                method="delete",
                path=f"/rest/routing/{route_id}",
            )
            await self._connection.request(api_request)

            logger.info(f"Delete static route command sent for {route_id}")

            # Invalidate cache
            self._connection._invalidate_cache(
                f"{CACHE_PREFIX_ROUTES}_{self._connection.site}"
            )

            return True

        except Exception as e:
            logger.error(f"Error deleting static route {route_id}: {e}", exc_info=True)
            return False
