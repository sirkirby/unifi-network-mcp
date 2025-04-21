"""
Traffic route tools for Unifi Network MCP server.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Iterable
import copy

from src.runtime import server, config, firewall_manager, network_manager
import mcp.types as types
from src.utils.permissions import parse_permission
from src.validator_registry import UniFiValidatorRegistry

logger = logging.getLogger(__name__) 

@server.tool(
    name="unifi_list_traffic_routes",
    description="List traffic routing rules (V2 API based) configured on the Unifi Network controller for the current site."
)
async def list_traffic_routes() -> Dict[str, Any]:
    """Lists all traffic routes (Policy-Based Routing rules) for the current UniFi site using the V2 API structure.

    Returns:
        A dictionary containing:
        - success (bool): Indicates if the operation was successful.
        - site (str): The identifier of the UniFi site queried.
        - count (int): The number of traffic routes found.
        - traffic_routes (List[Dict]): A list of traffic route rules, each containing fields based on the V2 API model, such as:
            - id (str): The unique identifier (_id) of the route.
            - name (str): The user-defined name of the route.
            - enabled (bool): Whether the route is currently active.
            - description (str, optional): User-provided description of the route.
            - interface (str): The network interface used (e.g., 'wan', 'wan2', 'vpnclient0').
            - matching_target (str): Destination/source type (e.g., 'INTERNET', 'DOMAIN', 'IP', 'REGION').
            - target_devices (List[Dict], optional): List of client devices or networks targeted (e.g., [{'type': 'CLIENT', 'client_mac': '...'}] or [{'type': 'NETWORK', 'network_id': '...'}]).
            - domains (List[Dict], optional): Domain targets if matching_target is 'DOMAIN'.
            - ip_addresses (List[Dict], optional): IP targets if matching_target is 'IP'.
            - regions (List[str], optional): Region targets if matching_target is 'REGION'.
            - network_id (str, optional): Specific network ID the route applies to.
            - kill_switch_enabled (bool, optional): VPN kill switch state.
            - next_hop (str, optional): Next hop IP for advanced routing.
            # Note: Exact fields depend on the specific route configuration and API version.
        - error (str, optional): An error message if the operation failed.

    Example response (success):
    {
        "success": True,
        "site": "default",
        "count": 1,
        "traffic_routes": [
            {
                "id": "61a7b8c9d0e1f2a3b4c5d6e7",
                "name": "Route Xbox via WAN2",
                "enabled": True,
                "description": "Route specific Xbox via WAN2",
                "interface": "wan2",
                "matching_target": "INTERNET",
                "target_devices": [
                    {
                        "type": "CLIENT",
                        "client_mac": "AA:BB:CC:DD:EE:FF"
                    }
                ],
                "domains": None,
                "ip_addresses": None,
                "regions": None,
                "network_id": null, 
                "kill_switch_enabled": false,
                "next_hop": null
            }
        ]
    }
    """
    if not parse_permission(config.permissions, "traffic_route", "read"):
        logger.warning(f"Permission denied for listing traffic routes.")
        return {"success": False, "error": "Permission denied to list traffic routes."}
    try:
        routes = await firewall_manager.get_traffic_routes()
        # Directly return the raw V2 data structure from the manager
        routes_raw = [r.raw if hasattr(r, "raw") and isinstance(r.raw, dict) else {} for r in routes]
        # Basic filtering to ensure only dicts are passed, log if not
        valid_routes_raw = []
        for idx, r_raw in enumerate(routes_raw):
             if isinstance(r_raw, dict) and r_raw.get("_id"):
                 valid_routes_raw.append(r_raw)
             else:
                  logger.warning(f"Skipping invalid/incomplete route data at index {idx}: {r_raw}")

        # Ensure serializability for JSON response
        serializable_routes = json.loads(json.dumps(valid_routes_raw, default=str))

        return {
            "success": True, 
            "site": firewall_manager._connection.site, 
            "count": len(serializable_routes), 
            "traffic_routes": serializable_routes
        }
    except Exception as e:
        logger.error(f"Error listing traffic routes: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_get_traffic_route_details",
    description="Get detailed configuration for a specific traffic route by ID (V2 API based)."
)
async def get_traffic_route_details(route_id: str) -> Dict[str, Any]:
    """Gets the detailed configuration of a specific traffic route by its ID using the V2 API structure.

    Args:
        route_id (str): The unique identifier (_id) of the traffic route.

    Returns:
        A dictionary containing:
        - success (bool): Indicates if the operation was successful.
        - route_id (str): The ID of the route requested.
        - details (Dict[str, Any]): A dictionary containing the raw configuration details
          of the traffic route as returned by the UniFi controller's V2 API. Fields will
          vary based on the route's configuration but may include `name`, `enabled`,
          `interface`, `matching_target`, `target_devices`, `domains`, `ip_addresses`, etc.
        - error (str, optional): An error message if the operation failed (e.g., route not found).

    Example response (success):
    {
        "success": True,
        "route_id": "61a7b8c9d0e1f2a3b4c5d6e7",
        "details": {
            "_id": "61a7b8c9d0e1f2a3b4c5d6e7",
            "name": "Route Specific Client via WAN2",
            "enabled": True,
            "description": "Route Client A via WAN2",
            "interface": "wan2",
            "matching_target": "INTERNET", # Route all internet traffic
            "target_devices": [ # For this specific client
                {
                    "type": "CLIENT",
                    "client_mac": "AA:BB:CC:DD:EE:FF"
                }
            ],
            "domains": null,
            "ip_addresses": null,
            "regions": null,
            "network_id": null,
            "kill_switch_enabled": false,
            "next_hop": null,
            "site_id": "..."
            # ... other potential fields
        }
    }
    """
    if not parse_permission(config.permissions, "traffic_route", "read"):
        logger.warning(f"Permission denied for getting traffic route details ({route_id}).")
        return {"success": False, "error": "Permission denied to get traffic route details."}
    try:
        if not route_id: return {"success": False, "error": "route_id is required"}
        routes = await firewall_manager.get_traffic_routes()
        # Find the specific route based on its raw data
        route_obj = next((r for r in routes if hasattr(r, "raw") and isinstance(r.raw, dict) and r.raw.get("_id") == route_id), None)
        
        if not route_obj or not route_obj.raw:
            return {"success": False, "error": f"Traffic route '{route_id}' not found or has invalid data."}
            
        # Return raw details - ensure serializable
        return {"success": True, "route_id": route_id, "details": json.loads(json.dumps(route_obj.raw, default=str))}
    except Exception as e:
        logger.error(f"Error getting traffic route details for {route_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_toggle_traffic_route",
    description="Enable or disable a specific traffic route by ID."
)
async def toggle_traffic_route(route_id: str, confirm: bool = False) -> Dict[str, Any]:
    """Enables or disables a specific traffic route. Requires confirmation.

    Args:
        route_id (str): The unique identifier (_id) of the traffic route to toggle.
        confirm (bool): Must be explicitly set to `True` to execute the toggle operation. Defaults to `False`.

    Returns:
        A dictionary containing:
        - success (bool): Indicates if the operation was successful.
        - route_id (str): The ID of the route that was toggled.
        - enabled (bool): The new state of the route (True if enabled, False if disabled).
        - message (str): A confirmation message indicating the action taken.
        - error (str, optional): An error message if the operation failed.

    Example response (success):
    {
        "success": True,
        "route_id": "61a7b8c9d0e1f2a3b4c5d6e7",
        "enabled": false,
        "message": "Traffic route 'Google DNS Route' (61a7b8c9d0e1f2a3b4c5d6e7) toggled to disabled."
    }
    """
    if not parse_permission(config.permissions, "traffic_route", "update"):
        logger.warning(f"Permission denied for toggling traffic route ({route_id}).")
        return {"success": False, "error": "Permission denied to toggle traffic route."}

    if not confirm: 
        logger.warning(f"Confirmation missing for toggling traffic route {route_id}.")
        return {"success": False, "error": "Confirmation required. Set 'confirm' to true."}
    
    try:
        routes = await firewall_manager.get_traffic_routes()
        route_obj = next((r for r in routes if r.id == route_id), None)
        if not route_obj or not route_obj.raw:
            return {"success": False, "error": f"Traffic route '{route_id}' not found."}
        route = route_obj.raw

        current_state = route.get("enabled", False)
        route_name = route.get("name", route_id)
        new_state = not current_state

        logger.info(f"Attempting to toggle traffic route '{route_name}' ({route_id}) to {new_state}")
        
        success = await firewall_manager.toggle_traffic_route(route_id)
        
        if success:
            toggled_route_obj = next((r for r in await firewall_manager.get_traffic_routes() if r.id == route_id), None)
            final_state = toggled_route_obj.enabled if toggled_route_obj else new_state
            
            logger.info(f"Successfully toggled traffic route '{route_name}' ({route_id}) to {final_state}")
            return {"success": True, 
                    "route_id": route_id,
                    "enabled": final_state,
                    "message": f"Traffic route '{route_name}' ({route_id}) toggled to {'enabled' if final_state else 'disabled'}."}
        else:
            logger.error(f"Failed to toggle traffic route '{route_name}' ({route_id}). Manager returned false.")
            route_after_toggle_obj = next((r for r in await firewall_manager.get_traffic_routes() if r.id == route_id), None)
            state_after = route_after_toggle_obj.enabled if route_after_toggle_obj else "unknown"
            return {"success": False, 
                    "route_id": route_id,
                    "state_after_attempt": state_after,
                    "error": f"Failed to toggle traffic route '{route_name}'. Check server logs."}
                    
    except Exception as e:
        logger.error(f"Error toggling traffic route {route_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_update_traffic_route",
    description="Update specific fields of an existing traffic route using V2 API schema. Requires confirmation."
)
async def update_traffic_route(
    route_id: str,
    update_data: Dict[str, Any],
    confirm: bool = False
) -> Dict[str, Any]:
    """Updates specific fields of an existing traffic route (Policy-Based Routing rule) using V2 API structure.

    Allows modifying properties based on the V2 schema (see `schemas.py` for TRAFFIC_ROUTE_UPDATE_SCHEMA).
    Common modifiable fields include: `description`, `enabled`, `matching_target`, `target_devices`,
    `domains`, `ip_addresses`, `regions`, `network_id`, `kill_switch_enabled`, `next_hop`.
    Note: `name` and `interface` are generally NOT updatable via this method/endpoint.
    Only provided fields in `update_data` are validated and sent for update.
    Requires confirmation.

    Args:
        route_id (str): The unique identifier (_id) of the traffic route to update.
        update_data (Dict[str, Any]): A dictionary containing the fields to update, matching the V2 schema.
            Example: `{"enabled": false, "description": "Disabled route"}`
            Example targeting change: `{"target_devices": [{"type": "NETWORK", "network_id": "..."}]}`
        confirm (bool): Must be explicitly set to `True` to execute the update. Defaults to `False`.

    Returns:
        A dictionary containing:
        - success (bool): Indicates if the operation was successful.
        - route_id (str): The ID of the route that was updated.
        - updated_fields (List[str]): Field names that were included in the update attempt.
        - details (Dict[str, Any]): Full details of the route *after* the update attempt, reflecting its current state.
        - error (str, optional): Error message if the operation failed.

    Example call:
    update_traffic_route(
        route_id="61a7b8c9d0e1f2a3b4c5d6e7",
        update_data={
            "enabled": False,
            "description": "Temporarily disabled"
        },
        confirm=True
    )

    Example response (success):
    {
        "success": True,
        "route_id": "61a7b8c9d0e1f2a3b4c5d6e7",
        "updated_fields": ["enabled", "description"],
        "details": { ... updated route details ... }
    }
    """
    if not parse_permission(config.permissions, "traffic_route", "update"):
        logger.warning(f"Permission denied for updating traffic route ({route_id}).")
        return {"success": False, "error": "Permission denied to update traffic route."}

    if not confirm:
        logger.warning(f"Confirmation missing for updating traffic route {route_id}.")
        return {"success": False, "error": "Confirmation required. Set 'confirm' to true."}

    if not route_id: return {"success": False, "error": "route_id is required"}
    if not update_data: return {"success": False, "error": "update_data cannot be empty"}

    # Use the V2 update schema for validation
    is_valid, error_msg, validated_data = UniFiValidatorRegistry.validate("traffic_route_update", update_data)
    if not is_valid:
        logger.warning(f"Invalid traffic route update data for ID {route_id}: {error_msg}")
        return {"success": False, "error": f"Invalid update data: {error_msg}"}
        
    if not validated_data:
        logger.warning(f"Traffic route update data for ID {route_id} is empty after validation.")
        return {"success": False, "error": "Update data is effectively empty or invalid."}

    try:
        # 1. Fetch existing route data (needed for context/logging, maybe not strictly for V2 PUT)
        routes = await firewall_manager.get_traffic_routes()
        existing_route_obj = next((r for r in routes if hasattr(r, "raw") and isinstance(r.raw, dict) and r.raw.get("_id") == route_id), None)
        if not existing_route_obj or not existing_route_obj.raw:
            return {"success": False, "error": f"Traffic route '{route_id}' not found for update."}
        
        route_name = existing_route_obj.raw.get("name", route_id) # For logging
        updated_fields_list = list(validated_data.keys())

        # 2. Call manager with only the validated update_data (V2 PUT often replaces/updates only provided fields)
        logger.info(f"Attempting to update traffic route '{route_name}' ({route_id}) with fields: {updated_fields_list}")
        # The manager's update_traffic_route is expected to handle the V2 PUT correctly
        # It might internally fetch and merge, or just send the partial update. Assuming it sends partial.
        success = await firewall_manager.update_traffic_route(route_id, validated_data) # Pass only validated changes
        
        # 3. Fetch again to get the *actual* state after update attempt
        updated_route_obj = next((r for r in await firewall_manager.get_traffic_routes() if hasattr(r, "raw") and isinstance(r.raw, dict) and r.raw.get("_id") == route_id), None)
        details_after_attempt = updated_route_obj.raw if updated_route_obj else {}

        if success:
            logger.info(f"Successfully submitted update for traffic route '{route_name}' ({route_id})")
            return {
                "success": True,
                "route_id": route_id,
                "updated_fields": updated_fields_list,
                "details": json.loads(json.dumps(details_after_attempt, default=str)) # Return state AFTER update
            }
        else:
            logger.error(f"Manager reported failure updating traffic route '{route_name}' ({route_id}).")
            return {
                "success": False, 
                "route_id": route_id,
                "error": f"Failed to update traffic route '{route_name}'. Check manager logs.",
                "details_after_attempt": json.loads(json.dumps(details_after_attempt, default=str)) # Still return state
            }

    except Exception as e:
        logger.error(f"Error updating traffic route {route_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_create_traffic_route",
    description="Create a new traffic route (Policy-Based Routing rule) using V2 API schema."
)
async def create_traffic_route(
    route_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a new traffic route using the V2 API structure with validation.
    
    Requires `name`, `interface`, `matching_target`, `network_id`, and `target_devices` in `route_data`.
    The structure of `route_data` should follow `TRAFFIC_ROUTE_SCHEMA` defined in `src/schemas.py`.

    Args:
        route_data (Dict[str, Any]): Dictionary containing the route configuration matching the V2 schema.
            - `name` (string): Name for the traffic route (Required).
            - `interface` (string): Interface to route through (e.g., "wan", "wan2", "vpnclient0") (Required).
            - `matching_target` (string): Specifies the destination/source type (e.g., "INTERNET", "DOMAIN", "IP", "REGION") (Required).
            - `network_id` (string): Network ID (LAN/VLAN) the route applies to (Required for creation).
            - `target_devices` (array): List of devices/networks the route applies to (Required, cannot be empty). Defines the source scope within network_id. Each item must be an object with `type` ('CLIENT' or 'NETWORK') and either `client_mac` (for CLIENT) or `network_id` (for NETWORK).
            - `domains` (array, optional): Required if `matching_target` is "DOMAIN". List of domain objects.
            - `ip_addresses` (array, optional): Required if `matching_target` is "IP". List of IP address objects.
            - `regions` (array, optional): Required if `matching_target` is "REGION". List of region strings.
            - `enabled` (boolean, optional): Default True.
            - `description` (string, optional): Description.
            - `kill_switch_enabled` (boolean, optional): Default False. For VPN interfaces.
            - `next_hop` (string, optional): Advanced routing option.

    Example targeting a specific device for all its internet traffic via WAN2:
    {
        "name": "Route Xbox via WAN2",
        "interface": "wan2",
        "matching_target": "INTERNET",
        "network_id": "abcdef1234567890abcdef01", # ID of the network the Xbox is on
        "target_devices": [
            {
                "type": "CLIENT",
                "client_mac": "AA:BB:CC:DD:EE:FF"
            }
        ],
        "enabled": true,
        "description": "Route specific Xbox client via WAN2"
    }
    
    Example targeting a whole network (VLAN) for specific domains via VPN:
    {
        "name": "Route Corp VLAN Domains via VPN",
        "interface": "vpnclient0",
        "matching_target": "DOMAIN",
        "network_id": "abcdef1234567890abcdef12", # ID of the Corp VLAN itself
        "target_devices": [ # Target the network itself as the source scope
             {
                 "type": "NETWORK",
                 "network_id": "abcdef1234567890abcdef12" # Same ID as network_id above
             }
        ],
        "domains": [
            {"domain": "example.com"},
            {"domain": "internal.corp"}
        ],
        "enabled": true
    }
    
    Returns:
        A dictionary containing:
        - success (bool): Whether the operation succeeded.
        - route_id (str): ID of the created route if successful.
        - message (str): Confirmation message if successful.
        - error (str): Error message if unsuccessful.
    """
    if not parse_permission(config.permissions, "traffic_route", "create"):
        logger.warning(f"Permission denied for creating traffic route.")
        return {"success": False, "error": "Permission denied to create traffic route."}
        
    is_valid, error_msg, validated_data = UniFiValidatorRegistry.validate("traffic_route", route_data)
    if not is_valid:
        logger.warning(f"Invalid traffic route data: {error_msg}")
        return {"success": False, "error": f"Validation error: {error_msg}"}

    # Additional semantic checks based on matching_target could still be useful
    matching_target = validated_data.get("matching_target")
    if matching_target == "DOMAIN" and not validated_data.get("domains"):
         return {"success": False, "error": "Field 'domains' is required when matching_target is 'DOMAIN'."}
    if matching_target == "IP" and not validated_data.get("ip_addresses"):
         return {"success": False, "error": "Field 'ip_addresses' is required when matching_target is 'IP'."}
    if matching_target == "REGION" and not validated_data.get("regions"):
         return {"success": False, "error": "Field 'regions' is required when matching_target is 'REGION'."}

    try:
        route_name = validated_data.get("name", "Unnamed Route")
        logger.info(f"Attempting to create traffic route '{route_name}' via interface '{validated_data.get('interface')}' with validated data.")
        
        # Explicitly build the payload using only fields defined in the schema
        # to avoid passing extraneous fields from LLM input.
        validator = UniFiValidatorRegistry.get_validator("traffic_route")
        if not validator:
             # This should ideally not happen if validation passed, but defensive check
             logger.error("Could not retrieve validator for 'traffic_route' after successful validation.")
             return {"success": False, "error": "Internal error: Validator not found after validation."}

        schema = validator.schema # Assuming ResourceValidator stores schema here
        schema_props = schema.get("properties", {}) if schema else {}
        payload_to_send = {k: v for k, v in validated_data.items() if k in schema_props}
        
        # Call the manager to create the route using the cleaned payload
        result = await firewall_manager.create_traffic_route(payload_to_send)

        if result and result.get("success"):
             # Manager indicates success
             new_id = result.get("route_id")
             logger.info(f"Manager reported success creating traffic route '{route_name}'. ID: {new_id}")
             return {
                 "success": True, 
                 "route_id": new_id, 
                 "message": f"Traffic route '{route_name}' created successfully (ID: {new_id})."
             }
        else:
            # Manager returned failure or unexpected response
            error_msg = result.get("error", "Unknown error during traffic route creation.") if isinstance(result, dict) else "Manager did not return a valid response."
            logger.error(f"Failed to create traffic route '{route_name}'. Manager returned: {result}")
            return {"success": False, "error": error_msg}

    except Exception as e:
        # Catch exceptions from validation or other unexpected issues
        logger.error(f"Error in create_traffic_route tool: {e}", exc_info=True)
        return {"success": False, "error": f"Tool error: {str(e)}"}

@server.tool(
    name="unifi_create_simple_traffic_route",
    description=(
        "Create a traffic route with a simplified high-level schema. "
        "Provides preview when confirm=false."
    )
)
async def create_simple_traffic_route(route: Dict[str, Any], confirm: bool = False) -> Dict[str, Any]:
    """LLM-friendly traffic route creation.

    Example schema:
    {
        "name": "US-Only via VPN",
        "interface": "vpnclient0",
        "network": "LAN",
        "matching_target": "REGION",
        "destinations": ["US"],
        "enabled": true
    }
    """

    if not parse_permission(config.permissions, "firewall", "create"):
        return {"success": False, "error": "Permission denied."}

    ok, err, validated = UniFiValidatorRegistry.validate("traffic_route_simple", route)
    if not ok:
        return {"success": False, "error": err}
    r = validated

    # Resolve network to id
    nets = await network_manager.get_networks()
    net_obj = next((n for n in nets if n.get("_id") == r["network"] or n.get("name") == r["network"]), None)
    if not net_obj:
        return {"success": False, "error": f"Network '{r['network']}' not found"}
    network_id = net_obj["_id"]

    # Build target_devices list
    if r.get("client_macs"):
        targets = [{"type": "CLIENT", "client_mac": m.lower()} for m in r["client_macs"]]
    else:
        targets = [{"type": "NETWORK", "network_id": network_id}]

    payload: Dict[str, Any] = {
        "name": r["name"],
        "interface": r["interface"],
        "network_id": network_id,
        "target_devices": targets,
        "matching_target": r["matching_target"],
        "enabled": r.get("enabled", True),
    }

    if r["matching_target"] == "DOMAIN":
        payload["domains"] = [{"domain": d} for d in r.get("destinations", [])]
    elif r["matching_target"] == "IP":
        payload["ip_addresses"] = [{"ip_or_subnet": ip} for ip in r.get("destinations", [])]
    elif r["matching_target"] == "REGION":
        payload["regions"] = r.get("destinations", [])
    # INTERNET needs no extra field

    if not confirm:
        return {"success": True, "preview": payload, "message": "Set confirm=true to apply"}

    created = await firewall_manager.create_traffic_route(payload)  # reuse existing method
    if isinstance(created, dict) and created.get("success"):
        return created
    if created is None:
        return {"success": False, "error": "Controller rejected creation"}
    return created