"""
MAC ACL rule tools for UniFi Network MCP server.

MAC ACL rules (Policy Engine) control Layer 2 access within a VLAN
by whitelisting specific MAC address pairs. Requires UniFi Network
Application with Policy Engine support.
"""

import json
import logging
from typing import Any, Dict, Optional

from src.runtime import acl_manager, config, server
from src.utils.confirmation import create_preview, should_auto_confirm
from src.utils.permissions import parse_permission

logger = logging.getLogger(__name__)


@server.tool(
    name="unifi_list_acl_rules",
    description="List MAC ACL rules (Policy Engine) for Layer 2 access control. "
    "These rules control which devices can communicate at Layer 2 within a VLAN.",
)
async def list_acl_rules(network_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Lists MAC ACL rules configured in the Policy Engine.

    Args:
        network_id (str, optional): Filter by network/VLAN ID.

    Returns:
        A dictionary containing:
        - success (bool): Indicates if the operation was successful.
        - count (int): Number of ACL rules found.
        - rules (List[Dict]): List of ACL rules with summary info.
    """
    if not parse_permission(config.permissions, "acl_rules", "read"):
        return {"success": False, "error": "Permission denied to list ACL rules."}

    try:
        rules = await acl_manager.get_acl_rules(network_id=network_id)
        formatted = [
            {
                "id": r.get("_id"),
                "name": r.get("name"),
                "acl_index": r.get("acl_index"),
                "action": r.get("action"),
                "enabled": r.get("enabled"),
                "network_id": r.get("mac_acl_network_id"),
                "source_type": r.get("traffic_source", {}).get("type"),
                "source_macs": r.get("traffic_source", {}).get("specific_mac_addresses", []),
                "destination_type": r.get("traffic_destination", {}).get("type"),
                "destination_macs": r.get("traffic_destination", {}).get("specific_mac_addresses", []),
            }
            for r in rules
        ]
        return {
            "success": True,
            "site": acl_manager._connection.site,
            "count": len(formatted),
            "rules": formatted,
        }
    except Exception as e:
        logger.error(f"Error listing ACL rules: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_get_acl_rule_details",
    description="Get detailed configuration for a specific MAC ACL rule by ID.",
)
async def get_acl_rule_details(rule_id: str) -> Dict[str, Any]:
    """
    Gets the detailed configuration of a specific MAC ACL rule.

    Args:
        rule_id (str): The unique identifier of the ACL rule.

    Returns:
        A dictionary containing the full rule configuration.
    """
    if not parse_permission(config.permissions, "acl_rules", "read"):
        return {"success": False, "error": "Permission denied to get ACL rule details."}

    try:
        if not rule_id:
            return {"success": False, "error": "rule_id is required"}

        rule = await acl_manager.get_acl_rule_by_id(rule_id)
        if not rule:
            # Fallback: search in list
            rules = await acl_manager.get_acl_rules()
            rule = next((r for r in rules if r.get("_id") == rule_id), None)

        if not rule:
            return {"success": False, "error": f"ACL rule '{rule_id}' not found."}

        return {
            "success": True,
            "rule_id": rule_id,
            "details": json.loads(json.dumps(rule, default=str)),
        }
    except Exception as e:
        logger.error(f"Error getting ACL rule {rule_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_create_acl_rule",
    description="Create a new MAC ACL rule for Layer 2 access control within a VLAN. "
    "Requires confirmation. IMPORTANT: traffic_source and traffic_destination type MUST be 'CLIENT_MAC' "
    "(not 'ANY'). Use an empty specific_mac_addresses list to match any device.",
    permission_category="acl_rules",
    permission_action="create",
)
async def create_acl_rule(
    name: str,
    acl_index: int,
    action: str,
    mac_acl_network_id: str,
    traffic_source: Optional[dict] = None,
    traffic_destination: Optional[dict] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """
    Creates a new MAC ACL rule in the Policy Engine.

    Args:
        name (str): Name of the rule.
        acl_index (int): Position in the rule chain (lower = evaluated first).
        action (str): "ALLOW" or "BLOCK".
        mac_acl_network_id (str): Network ID of the VLAN this rule applies to.
        traffic_source (dict): Source config with keys:
            - type (str): "CLIENT_MAC"
            - specific_mac_addresses (list): List of source MAC addresses. Empty list = any.
        traffic_destination (dict): Destination config with same structure as source.
        confirm (bool): Must be True to execute. False returns a preview.

    Returns:
        Preview of changes or the created rule.
    """
    if traffic_source is None:
        traffic_source = {
            "ips_or_subnets": [],
            "network_ids": [],
            "ports": [],
            "specific_mac_addresses": [],
            "type": "CLIENT_MAC",
        }
    if traffic_destination is None:
        traffic_destination = {
            "ips_or_subnets": [],
            "network_ids": [],
            "ports": [],
            "specific_mac_addresses": [],
            "type": "CLIENT_MAC",
        }

    rule_data = {
        "name": name,
        "acl_index": acl_index,
        "action": action.upper(),
        "enabled": True,
        "mac_acl_network_id": mac_acl_network_id,
        "specific_enforcers": [],
        "traffic_source": traffic_source,
        "traffic_destination": traffic_destination,
        "type": "MAC",
    }

    if not confirm and not should_auto_confirm():
        return create_preview(
            resource_type="acl_rule",
            resource_data=rule_data,
            resource_name=name,
        )

    try:
        result = await acl_manager.create_acl_rule(rule_data)
        if result:
            return {
                "success": True,
                "message": f"ACL rule '{name}' created successfully.",
                "rule": json.loads(json.dumps(result, default=str)),
            }
        return {"success": False, "error": "Failed to create ACL rule."}
    except Exception as e:
        logger.error(f"Error creating ACL rule: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_update_acl_rule",
    description="Update an existing MAC ACL rule. Requires the full rule object (PUT replaces entire resource). "
    "Requires confirmation. IMPORTANT: traffic source/destination type MUST be 'CLIENT_MAC' (not 'ANY').",
    permission_category="acl_rules",
    permission_action="update",
)
async def update_acl_rule(rule_id: str, rule_data: dict, confirm: bool = False) -> Dict[str, Any]:
    """
    Updates an existing MAC ACL rule.

    Args:
        rule_id (str): The ID of the rule to update.
        rule_data (dict): The complete updated rule object (PUT replaces the entire resource).
        confirm (bool): Must be True to execute.

    Returns:
        Preview of changes or success/failure status.
    """
    if not confirm and not should_auto_confirm():
        return create_preview(
            resource_type="acl_rule",
            resource_data=rule_data,
            resource_name=rule_id,
        )

    try:
        success = await acl_manager.update_acl_rule(rule_id, rule_data)
        if success:
            return {"success": True, "message": f"ACL rule '{rule_id}' updated successfully."}
        return {"success": False, "error": f"Failed to update ACL rule '{rule_id}'."}
    except Exception as e:
        logger.error(f"Error updating ACL rule {rule_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_delete_acl_rule",
    description="Delete a MAC ACL rule. Requires confirmation. WARNING: Removing an ALLOW rule "
    "may block device communication. Removing a BLOCK rule may open access.",
    permission_category="acl_rules",
    permission_action="update",
)
async def delete_acl_rule(rule_id: str, confirm: bool = False) -> Dict[str, Any]:
    """
    Deletes a MAC ACL rule.

    Args:
        rule_id (str): The ID of the rule to delete.
        confirm (bool): Must be True to execute.

    Returns:
        Preview or success/failure status.
    """
    if not confirm and not should_auto_confirm():
        return create_preview(
            resource_type="acl_rule",
            resource_data={"rule_id": rule_id},
            resource_name=rule_id,
            warnings=["Removing an ALLOW rule may block device communication. Removing a BLOCK rule may open access."],
        )

    try:
        success = await acl_manager.delete_acl_rule(rule_id)
        if success:
            return {"success": True, "message": f"ACL rule '{rule_id}' deleted successfully."}
        return {"success": False, "error": f"Failed to delete ACL rule '{rule_id}'."}
    except Exception as e:
        logger.error(f"Error deleting ACL rule {rule_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
