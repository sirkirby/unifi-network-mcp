"""Static routing tools for UniFi Network MCP server.

Provides MCP tools for managing static routes on the UniFi controller.
Static routes allow for advanced routing configuration to direct traffic
through specific gateways or interfaces.
"""

import logging
import json
from typing import Dict, Any, Optional

from src.runtime import server, config
from src.utils.permissions import parse_permission

logger = logging.getLogger(__name__)


def _get_routing_manager():
    """Lazy import to avoid circular dependency."""
    from src.runtime import routing_manager
    return routing_manager


@server.tool(
    name="unifi_list_routes",
    description="List all static routes configured on the UniFi controller.",
)
async def list_routes() -> Dict[str, Any]:
    """Lists all static routes configured for the current UniFi site.

    Static routes allow you to define custom routing paths for specific
    network destinations through specified next-hop gateways.

    Returns:
        A dictionary containing:
        - success (bool): Indicates if the operation was successful.
        - site (str): The identifier of the UniFi site queried.
        - count (int): The number of routes found.
        - routes (List[Dict]): A list of static routes with:
            - id (str): The unique identifier (_id) of the route.
            - name (str): The name of the route.
            - network (str): The destination network (CIDR).
            - nexthop (str): The next-hop IP or interface.
            - distance (int): Administrative distance.
            - enabled (bool): Whether the route is active.
            - type (str): Route type.
        - error (str, optional): An error message if the operation failed.

    Example response:
    {
        "success": True,
        "site": "default",
        "count": 2,
        "routes": [
            {
                "id": "60d4e5f6a7b8c9d0e1f2a3b4",
                "name": "VPN Network",
                "network": "10.0.0.0/8",
                "nexthop": "192.168.1.1",
                "distance": 1,
                "enabled": true,
                "type": "nexthop-route"
            }
        ]
    }
    """
    if not parse_permission(config.permissions, "route", "read"):
        logger.warning("Permission denied for listing static routes.")
        return {"success": False, "error": "Permission denied to list static routes."}

    try:
        routing_manager = _get_routing_manager()
        routes = await routing_manager.get_routes()

        formatted_routes = []
        for r in routes:
            formatted_routes.append({
                "id": r.get("_id"),
                "name": r.get("name"),
                "network": r.get("static-route_network"),
                "nexthop": r.get("static-route_nexthop"),
                "distance": r.get("static-route_distance", 1),
                "enabled": r.get("enabled", True),
                "type": r.get("type", "nexthop-route"),
            })

        return {
            "success": True,
            "site": routing_manager._connection.site,
            "count": len(formatted_routes),
            "routes": formatted_routes,
        }
    except Exception as e:
        logger.error(f"Error listing static routes: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_get_route_details",
    description="Get details for a specific static route by ID.",
)
async def get_route_details(route_id: str) -> Dict[str, Any]:
    """Gets the detailed information of a specific static route by its ID.

    Args:
        route_id (str): The unique identifier (_id) of the static route.

    Returns:
        A dictionary containing:
        - success (bool): Indicates if the operation was successful.
        - site (str): The identifier of the UniFi site queried.
        - route_id (str): The ID of the route requested.
        - details (Dict[str, Any]): Full route details from the controller.
        - error (str, optional): An error message if the operation failed.
    """
    if not parse_permission(config.permissions, "route", "read"):
        logger.warning(f"Permission denied for getting route details ({route_id}).")
        return {"success": False, "error": "Permission denied to get route details."}

    try:
        if not route_id:
            return {"success": False, "error": "route_id is required"}

        routing_manager = _get_routing_manager()
        route = await routing_manager.get_route_details(route_id)

        if route:
            return {
                "success": True,
                "site": routing_manager._connection.site,
                "route_id": route_id,
                "details": json.loads(json.dumps(route, default=str)),
            }
        else:
            return {
                "success": False,
                "error": f"Static route with ID '{route_id}' not found.",
            }
    except Exception as e:
        logger.error(f"Error getting route {route_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_create_route",
    description=(
        "Create a new static route for custom network routing. "
        "Requires confirmation."
    ),
    permission_category="routes",
    permission_action="create",
)
async def create_route(
    name: str,
    network: str,
    nexthop: str,
    distance: int = 1,
    enabled: bool = True,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Creates a new static route on the UniFi controller.

    Static routes direct traffic destined for specific networks through
    a specified next-hop gateway or interface.

    Args:
        name (str): Name of the static route (for identification).
        network (str): Destination network in CIDR notation (e.g., '10.0.0.0/8').
        nexthop (str): Next-hop IP address (e.g., '192.168.1.1') or interface.
        distance (int, optional): Administrative distance/metric (default 1).
            Lower values have higher priority.
        enabled (bool, optional): Whether the route is active (default True).
        confirm (bool): Must be True to execute. Defaults to False.

    Returns:
        A dictionary containing:
        - success (bool): Whether the operation succeeded.
        - site (str): The UniFi site.
        - route_id (str): ID of the created route.
        - details (Dict): The created route details.
        - error (str, optional): Error message if failed.

    Example:
        Create a route for VPN traffic:
        {
            "name": "VPN Network Route",
            "network": "10.0.0.0/8",
            "nexthop": "192.168.1.254",
            "distance": 1,
            "enabled": true,
            "confirm": true
        }
    """
    if not parse_permission(config.permissions, "route", "create"):
        logger.warning("Permission denied for creating static route.")
        return {"success": False, "error": "Permission denied to create static route."}

    if not confirm:
        return {
            "success": False,
            "error": "Confirmation required. Set 'confirm' to true.",
            "preview": {
                "name": name,
                "network": network,
                "nexthop": nexthop,
                "distance": distance,
                "enabled": enabled,
            },
        }

    if not name or not name.strip():
        return {"success": False, "error": "name is required and cannot be empty"}

    if not network or not network.strip():
        return {"success": False, "error": "network is required (CIDR notation)"}

    if not nexthop or not nexthop.strip():
        return {"success": False, "error": "nexthop is required"}

    try:
        routing_manager = _get_routing_manager()

        # Check if name already exists
        existing = await routing_manager.get_route_by_name(name)
        if existing:
            return {
                "success": False,
                "error": f"Static route with name '{name}' already exists.",
            }

        logger.info(f"Creating static route '{name}' -> {network} via {nexthop}")

        created_route = await routing_manager.create_route(
            name=name,
            static_route_network=network,
            static_route_nexthop=nexthop,
            static_route_distance=distance,
            enabled=enabled,
        )

        if created_route:
            return {
                "success": True,
                "site": routing_manager._connection.site,
                "message": f"Static route '{name}' created successfully.",
                "route_id": created_route.get("_id"),
                "details": json.loads(json.dumps(created_route, default=str)),
            }
        else:
            return {
                "success": False,
                "error": "Failed to create static route. Check server logs.",
            }

    except Exception as e:
        logger.error(f"Error creating static route '{name}': {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_update_route",
    description="Update an existing static route. Requires confirmation.",
    permission_category="routes",
    permission_action="update",
)
async def update_route(
    route_id: str,
    name: Optional[str] = None,
    network: Optional[str] = None,
    nexthop: Optional[str] = None,
    distance: Optional[int] = None,
    enabled: Optional[bool] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Updates an existing static route's settings.

    Only provide the fields you want to change. Omitted fields remain unchanged.

    Args:
        route_id (str): The unique identifier (_id) of the route to update.
        name (str, optional): New name for the route.
        network (str, optional): New destination network (CIDR).
        nexthop (str, optional): New next-hop IP or interface.
        distance (int, optional): New administrative distance.
        enabled (bool, optional): Enable/disable the route.
        confirm (bool): Must be True to execute. Defaults to False.

    Returns:
        A dictionary containing:
        - success (bool): Whether the operation succeeded.
        - route_id (str): The ID of the updated route.
        - message (str): Confirmation message.
        - details (Dict): Updated route details.
        - error (str, optional): Error message if failed.
    """
    if not parse_permission(config.permissions, "route", "update"):
        logger.warning(f"Permission denied for updating static route ({route_id}).")
        return {"success": False, "error": "Permission denied to update static route."}

    if not route_id:
        return {"success": False, "error": "route_id is required"}

    # Check if any update field is provided
    if all(v is None for v in [name, network, nexthop, distance, enabled]):
        return {"success": False, "error": "At least one field to update must be provided."}

    routing_manager = _get_routing_manager()

    if not confirm:
        # Fetch current state for preview
        route = await routing_manager.get_route_details(route_id)
        if not route:
            return {
                "success": False,
                "error": f"Static route with ID '{route_id}' not found.",
            }
        return {
            "success": False,
            "error": "Confirmation required. Set 'confirm' to true.",
            "preview": {
                "route_id": route_id,
                "current_name": route.get("name"),
                "new_name": name,
                "current_network": route.get("static-route_network"),
                "new_network": network,
                "current_nexthop": route.get("static-route_nexthop"),
                "new_nexthop": nexthop,
                "current_distance": route.get("static-route_distance"),
                "new_distance": distance,
                "current_enabled": route.get("enabled"),
                "new_enabled": enabled,
            },
        }

    try:
        logger.info(f"Updating static route {route_id}")

        success = await routing_manager.update_route(
            route_id=route_id,
            name=name,
            static_route_network=network,
            static_route_nexthop=nexthop,
            static_route_distance=distance,
            enabled=enabled,
        )

        if success:
            # Fetch updated route
            updated_route = await routing_manager.get_route_details(route_id)
            return {
                "success": True,
                "route_id": route_id,
                "message": f"Static route '{route_id}' updated successfully.",
                "details": json.loads(json.dumps(updated_route, default=str)),
            }
        else:
            return {
                "success": False,
                "error": f"Failed to update static route {route_id}. Check server logs.",
            }

    except Exception as e:
        logger.error(f"Error updating static route {route_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
