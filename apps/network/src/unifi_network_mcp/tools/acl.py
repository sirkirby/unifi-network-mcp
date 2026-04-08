"""
MAC ACL rule tools for UniFi Network MCP server.

MAC ACL rules (Policy Engine) control Layer 2 access within a VLAN
by whitelisting specific MAC address pairs. Requires UniFi Network
Application with Policy Engine support.
"""

import json
import logging
from typing import Annotated, Any, Dict, List, Optional

from mcp.types import ToolAnnotations
from pydantic import Field

from unifi_mcp_shared.confirmation import create_preview, update_preview
from unifi_network_mcp.runtime import acl_manager, server
from unifi_network_mcp.validator_registry import UniFiValidatorRegistry

logger = logging.getLogger(__name__)


@server.tool(
    name="unifi_list_acl_rules",
    description="List MAC ACL rules (Policy Engine) for Layer 2 access control. "
    "These rules control which devices can communicate at Layer 2 within a VLAN.",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def list_acl_rules(
    network_id: Annotated[
        Optional[str],
        Field(description="Filter rules by network/VLAN ID (from unifi_list_networks). Omit to list all ACL rules"),
    ] = None,
) -> Dict[str, Any]:
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
        logger.error("Error listing ACL rules: %s", e, exc_info=True)
        return {"success": False, "error": f"Failed to list ACL rules: {e}"}


@server.tool(
    name="unifi_get_acl_rule_details",
    description="Get detailed configuration for a specific MAC ACL rule by ID.",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def get_acl_rule_details(
    rule_id: Annotated[str, Field(description="Unique identifier (_id) of the ACL rule (from unifi_list_acl_rules)")],
) -> Dict[str, Any]:
    """
    Gets the detailed configuration of a specific MAC ACL rule.

    Args:
        rule_id (str): The unique identifier of the ACL rule.

    Returns:
        A dictionary containing the full rule configuration.
    """
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
        logger.error("Error getting ACL rule %s: %s", rule_id, e, exc_info=True)
        return {"success": False, "error": f"Failed to get ACL rule {rule_id}: {e}"}


@server.tool(
    name="unifi_create_acl_rule",
    description="Create a new MAC ACL rule for Layer 2 access control within a VLAN. "
    "Use source_macs/destination_macs to specify MAC addresses (same field names as unifi_list_acl_rules output). "
    "Empty list = match any device. Requires confirmation.",
    permission_category="acl_rules",
    permission_action="create",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
)
async def create_acl_rule(
    name: Annotated[str, Field(description="Descriptive name for the ACL rule")],
    acl_index: Annotated[int, Field(description="Position in the rule chain (lower numbers are evaluated first)")],
    action: Annotated[str, Field(description="Rule action: 'ALLOW' or 'BLOCK'")],
    mac_acl_network_id: Annotated[
        str,
        Field(description="Network/VLAN ID this rule applies to (from unifi_list_networks)"),
    ],
    source_macs: Annotated[
        Optional[List[str]],
        Field(
            description="List of source MAC addresses to match (empty list = any source). Uses same field name as unifi_list_acl_rules output"
        ),
    ] = None,
    destination_macs: Annotated[
        Optional[List[str]],
        Field(
            description="List of destination MAC addresses to match (empty list = any destination). Uses same field name as unifi_list_acl_rules output"
        ),
    ] = None,
    traffic_source: Annotated[
        Optional[dict],
        Field(
            description="(Advanced) Full source config dict. Ignored if source_macs is provided. Keys: type ('CLIENT_MAC'), specific_mac_addresses (list of MACs)"
        ),
    ] = None,
    traffic_destination: Annotated[
        Optional[dict],
        Field(
            description="(Advanced) Full destination config dict. Ignored if destination_macs is provided. Keys: type ('CLIENT_MAC'), specific_mac_addresses (list of MACs)"
        ),
    ] = None,
    confirm: Annotated[
        bool,
        Field(description="When true, creates the rule. When false (default), returns a preview of the changes"),
    ] = False,
) -> Dict[str, Any]:
    """
    Creates a new MAC ACL rule in the Policy Engine.

    Args:
        name (str): Name of the rule.
        acl_index (int): Position in the rule chain (lower = evaluated first).
        action (str): "ALLOW" or "BLOCK".
        mac_acl_network_id (str): Network ID of the VLAN this rule applies to.
        source_macs (list): List of source MAC addresses. Empty list or None = any.
        destination_macs (list): List of destination MAC addresses. Empty list or None = any.
        traffic_source (dict): Advanced — full source config dict. Ignored if source_macs is provided.
        traffic_destination (dict): Advanced — full destination config dict. Ignored if destination_macs is provided.
        confirm (bool): Must be True to execute. False returns a preview.

    Returns:
        Preview of changes or the created rule.
    """
    logger.info("unifi_create_acl_rule called (name=%s, action=%s, confirm=%s)", name, action, confirm)
    # Build traffic_source: convenience params take precedence over raw dicts
    if source_macs is not None:
        traffic_source = {
            "ips_or_subnets": [],
            "network_ids": [],
            "ports": [],
            "specific_mac_addresses": source_macs,
            "type": "CLIENT_MAC",
        }
    elif traffic_source is None:
        traffic_source = {
            "ips_or_subnets": [],
            "network_ids": [],
            "ports": [],
            "specific_mac_addresses": [],
            "type": "CLIENT_MAC",
        }
    # Build traffic_destination: same precedence
    if destination_macs is not None:
        traffic_destination = {
            "ips_or_subnets": [],
            "network_ids": [],
            "ports": [],
            "specific_mac_addresses": destination_macs,
            "type": "CLIENT_MAC",
        }
    elif traffic_destination is None:
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

    if not confirm:
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
        logger.error("Error creating ACL rule: %s", e, exc_info=True)
        return {"success": False, "error": f"Failed to create ACL rule: {e}"}


@server.tool(
    name="unifi_update_acl_rule",
    description="Update an existing MAC ACL rule. Pass only the fields you want to change — "
    "current values are automatically preserved. "
    "Requires confirmation. Use source_macs/destination_macs for MAC lists (same field names as list output). "
    "If using advanced traffic_source/traffic_destination dicts instead, type MUST be 'CLIENT_MAC'.",
    permission_category="acl_rules",
    permission_action="update",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
)
async def update_acl_rule(
    rule_id: Annotated[
        str, Field(description="Unique identifier (_id) of the ACL rule to update (from unifi_list_acl_rules)")
    ],
    rule_data: Annotated[
        dict,
        Field(
            description="Dictionary of fields to update. Pass only the fields you want to change — "
            "current values are automatically preserved. "
            "Allowed keys: name, acl_index, action ('ALLOW'/'BLOCK'), enabled (bool), "
            "mac_acl_network_id, source_macs (list of MACs), destination_macs (list of MACs), "
            "traffic_source (dict, advanced), traffic_destination (dict, advanced)"
        ),
    ],
    confirm: Annotated[
        bool,
        Field(description="When true, applies the update. When false (default), returns a preview of the changes"),
    ] = False,
) -> Dict[str, Any]:
    """Updates an existing MAC ACL rule with partial data."""
    logger.info("unifi_update_acl_rule called (rule_id=%s, confirm=%s)", rule_id, confirm)
    if not rule_id:
        return {"success": False, "error": "rule_id is required"}
    if not rule_data:
        return {"success": False, "error": "rule_data cannot be empty"}

    # Convenience params and advanced dicts are mutually exclusive — reject
    # the collision up front rather than silently picking a winner (which
    # would be the same class of silent-drop bug this tool's create path
    # exists to prevent).
    if "source_macs" in rule_data and "traffic_source" in rule_data:
        return {
            "success": False,
            "error": "Pass either source_macs or traffic_source, not both.",
        }
    if "destination_macs" in rule_data and "traffic_destination" in rule_data:
        return {
            "success": False,
            "error": "Pass either destination_macs or traffic_destination, not both.",
        }

    # Translate flattened field names (from list output) to nested structure
    if "source_macs" in rule_data:
        rule_data["traffic_source"] = {
            "ips_or_subnets": [],
            "network_ids": [],
            "ports": [],
            "specific_mac_addresses": rule_data.pop("source_macs"),
            "type": "CLIENT_MAC",
        }
    if "destination_macs" in rule_data:
        rule_data["traffic_destination"] = {
            "ips_or_subnets": [],
            "network_ids": [],
            "ports": [],
            "specific_mac_addresses": rule_data.pop("destination_macs"),
            "type": "CLIENT_MAC",
        }

    is_valid, error_msg, validated_data = UniFiValidatorRegistry.validate("acl_rule_update", rule_data)
    if not is_valid:
        return {"success": False, "error": f"Invalid update data: {error_msg}"}
    if not validated_data:
        return {"success": False, "error": "Update data is effectively empty or invalid."}

    current = await acl_manager.get_acl_rule_by_id(rule_id)
    if not current:
        return {"success": False, "error": f"ACL rule '{rule_id}' not found."}

    if not confirm:
        return update_preview(
            resource_type="acl_rule",
            resource_id=rule_id,
            resource_name=current.get("name"),
            current_state=current,
            updates=validated_data,
        )

    try:
        success = await acl_manager.update_acl_rule(rule_id, validated_data)
        if success:
            return {"success": True, "message": f"ACL rule '{rule_id}' updated successfully."}
        return {"success": False, "error": f"Failed to update ACL rule '{rule_id}'."}
    except Exception as e:
        logger.error("Error updating ACL rule %s: %s", rule_id, e, exc_info=True)
        return {"success": False, "error": f"Failed to update ACL rule {rule_id}: {e}"}


@server.tool(
    name="unifi_delete_acl_rule",
    description="Delete a MAC ACL rule. Requires confirmation. WARNING: Removing an ALLOW rule "
    "may block device communication. Removing a BLOCK rule may open access.",
    permission_category="acl_rules",
    permission_action="delete",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=False),
)
async def delete_acl_rule(
    rule_id: Annotated[
        str, Field(description="Unique identifier (_id) of the ACL rule to delete (from unifi_list_acl_rules)")
    ],
    confirm: Annotated[
        bool,
        Field(
            description="When true, deletes the rule. When false (default), returns a preview. WARNING: Removing an ALLOW rule may block device communication"
        ),
    ] = False,
) -> Dict[str, Any]:
    """
    Deletes a MAC ACL rule.

    Args:
        rule_id (str): The ID of the rule to delete.
        confirm (bool): Must be True to execute.

    Returns:
        Preview or success/failure status.
    """
    if not confirm:
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
        logger.error("Error deleting ACL rule %s: %s", rule_id, e, exc_info=True)
        return {"success": False, "error": f"Failed to delete ACL rule {rule_id}: {e}"}
