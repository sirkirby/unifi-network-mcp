"""
QoS tools for Unifi Network MCP server.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Iterable

from src.runtime import server, config, qos_manager
import mcp.types as types # Import the types module
from src.utils.permissions import parse_permission
from src.validator_registry import UniFiValidatorRegistry # Added

logger = logging.getLogger(__name__)

@server.tool(
    name="unifi_list_qos_rules",
    description="List all QoS rules on the Unifi Network controller for the current site."
)
async def list_qos_rules() -> Dict[str, Any]:
    """Lists all Quality of Service (QoS) rules configured for the current UniFi site.

    Returns:
        A dictionary containing:
        - success (bool): Indicates if the operation was successful.
        - site (str): The identifier of the UniFi site queried.
        - count (int): The number of QoS rules found.
        - qos_rules (List[Dict]): A list of QoS rules, each containing summary info:
            - id (str): The unique identifier (_id) of the rule.
            - name (str): The user-defined name of the rule.
            - enabled (bool): Whether the rule is currently active.
            # Add other simple summary fields if available and useful
        - error (str, optional): An error message if the operation failed.

    Example response (success):
    {
        "success": True,
        "site": "default",
        "count": 1,
        "qos_rules": [
            {
                "id": "60d4e5f6a7b8c9d0e1f2a3b4",
                "name": "VoIP Prioritization",
                "enabled": True
            }
        ]
    }
    """
    # Basic permission check (optional for read-only, but good practice)
    if not parse_permission(config.permissions, "qos", "read"):
        logger.warning(f"Permission denied for listing QoS rules.")
        return {"success": False, "error": "Permission denied to list QoS rules."}
    try:
        qos_rules = await qos_manager.get_qos_rules()
        rules_raw = [r.raw if hasattr(r, "raw") else r for r in qos_rules]
        formatted_rules = [
            {
             "id": r.get("_id"), 
             "name": r.get("name"), 
             "enabled": r.get("enabled")
             # Add other fields as needed for summary
             }
            for r in rules_raw
        ]
        return {"success": True, "site": qos_manager._connection.site, "count": len(formatted_rules), "qos_rules": formatted_rules}
    except Exception as e:
        logger.error(f"Error listing QoS rules: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_get_qos_rule_details",
    description="Get details for a specific QoS rule by ID."
)
async def get_qos_rule_details(rule_id: str) -> Dict[str, Any]:
    """Gets the detailed configuration of a specific QoS rule by its ID.

    Args:
        rule_id (str): The unique identifier (_id) of the QoS rule.

    Returns:
        A dictionary containing:
        - success (bool): Indicates if the operation was successful.
        - site (str): The identifier of the UniFi site queried.
        - rule_id (str): The ID of the rule requested.
        - details (Dict[str, Any]): A dictionary containing the raw configuration details
          of the QoS rule as returned by the UniFi controller.
        - error (str, optional): An error message if the operation failed (e.g., rule not found).

    Example response (success):
    {
        "success": True,
        "site": "default",
        "rule_id": "60d4e5f6a7b8c9d0e1f2a3b4",
        "details": {
            "_id": "60d4e5f6a7b8c9d0e1f2a3b4",
            "name": "VoIP Prioritization",
            "enabled": True,
            "interface": "WAN",
            "direction": "upload",
            "bandwidth_limit_kbps": 500,
            "dscp_value": 46,
            "site_id": "...",
            # ... other fields
        }
    }
    """
    if not parse_permission(config.permissions, "qos", "read"):
        logger.warning(f"Permission denied for getting QoS rule details ({rule_id}).")
        return {"success": False, "error": "Permission denied to get QoS rule details."}
    try:
        if not rule_id:
             return {"success": False, "error": "rule_id is required"}
        # Assuming manager returns the raw dict or None
        rule = await qos_manager.get_qos_rule_details(rule_id) 
        if rule:
            # Return details - ensure serializable (using json.loads/dumps for safety)
            return {"success": True, "site": qos_manager._connection.site, "rule_id": rule_id, "details": json.loads(json.dumps(rule, default=str))}
        else:
            return {"success": False, "error": f"QoS rule with ID \'{rule_id}\' not found."}
    except Exception as e:
        logger.error(f"Error getting QoS rule {rule_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_toggle_qos_rule_enabled", # Renamed from update_qos_rule_state
    description="Enable or disable a specific QoS rule by ID. Requires confirmation."
)
async def toggle_qos_rule_enabled(rule_id: str, confirm: bool = False) -> Dict[str, Any]: # Removed 'enabled' param
    """Enables or disables a specific QoS rule. Requires confirmation.

    Args:
        rule_id (str): The unique identifier (_id) of the QoS rule to toggle.
        confirm (bool): Must be explicitly set to `True` to execute the toggle operation. Defaults to `False`.

    Returns:
        A dictionary containing:
        - success (bool): Indicates if the operation was successful.
        - rule_id (str): The ID of the rule toggled.
        - enabled (bool): The new state of the rule (True if enabled, False if disabled).
        - message (str): A confirmation message.
        - error (str, optional): An error message if the operation failed.

    Example response (success):
    {
        "success": True,
        "rule_id": "60d4e5f6a7b8c9d0e1f2a3b4",
        "enabled": false,
        "message": "QoS rule 'VoIP Prioritization' (60d4e5f6a7b8c9d0e1f2a3b4) toggled to disabled."
    }
    """
    if not parse_permission(config.permissions, "qos", "update"):
        logger.warning(f"Permission denied for updating QoS rule state ({rule_id}).")
        return {"success": False, "error": "Permission denied to update QoS rule state."}

    if not confirm:
        logger.warning(f"Confirmation missing for toggling QoS rule {rule_id}.")
        return {"success": False, "error": "Confirmation required. Set 'confirm' to true."}

    if not rule_id: return {"success": False, "error": "rule_id is required"}

    try:
        # Fetch the rule first to determine current state and name
        rule = await qos_manager.get_qos_rule_details(rule_id)
        if not rule:
            return {"success": False, "error": f"QoS rule with ID '{rule_id}' not found."}
        
        current_state = rule.get("enabled", False)
        new_state = not current_state
        rule_name = rule.get("name", rule_id)
        
        logger.info(f"Attempting to toggle QoS rule '{rule_name}' ({rule_id}) to {new_state}")

        update_data = {"enabled": new_state}
        # Assuming qos_manager.update_qos_rule handles fetch-merge-put or accepts partial data
        # If it requires full object, this needs adjustment in the manager.
        success = await qos_manager.update_qos_rule(rule_id, update_data) 
        
        if success:
            # Fetch again to confirm state
            rule_after_toggle = await qos_manager.get_qos_rule_details(rule_id)
            final_state = rule_after_toggle.get("enabled", new_state) if rule_after_toggle else new_state
            
            logger.info(f"Successfully toggled QoS rule '{rule_name}' ({rule_id}) enabled status to {final_state}")
            return {"success": True, 
                    "rule_id": rule_id, 
                    "enabled": final_state, 
                    "message": f"QoS rule '{rule_name}' ({rule_id}) toggled to {'enabled' if final_state else 'disabled'}."}
        else:
            logger.error(f"Failed to toggle QoS rule '{rule_name}' ({rule_id}). Manager returned false.")
            # Fetch state after failure
            rule_after_fail = await qos_manager.get_qos_rule_details(rule_id)
            state_after = rule_after_fail.get("enabled", "unknown") if rule_after_fail else "unknown"
            return {"success": False, 
                    "rule_id": rule_id,
                    "state_after_attempt": state_after,
                    "error": f"Failed to toggle QoS rule '{rule_name}' ({rule_id}). Check server logs."}
                    
    except Exception as e:
        logger.error(f"Error toggling QoS rule {rule_id} state: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

# --- NEW UPDATE QOS RULE TOOL ---
@server.tool(
    name="unifi_update_qos_rule",
    description="Update specific fields of an existing QoS rule. Requires confirmation."
)
async def update_qos_rule(
    rule_id: str,
    update_data: Dict[str, Any],
    confirm: bool = False
) -> Dict[str, Any]:
    """Updates specific fields of an existing Quality of Service (QoS) rule.

    Allows modifying properties like name, bandwidth limits, targeting, DSCP values, etc.
    Only provided fields are updated. Requires confirmation.

    Args:
        rule_id (str): The unique identifier (_id) of the QoS rule to update.
        update_data (Dict[str, Any]): Dictionary of fields to update.
            Allowed fields (all optional):
            - name (string): New name for the rule.
            - interface (string): New interface (e.g., 'WAN', 'LAN').
            - direction (string): New direction ('upload', 'download').
            - bandwidth_limit_kbps (integer): New bandwidth limit in Kbps.
            - target_ip_address (string): New target IP address.
            - target_subnet (string): New target subnet (CIDR).
            - dscp_value (integer): New DSCP value (0-63).
            - enabled (boolean): New enabled state.
        confirm (bool): Must be set to `True` to execute. Defaults to `False`.

    Returns:
        Dict: Success status, ID, updated fields, details, or error message.
        Example (success):
        {
            "success": True,
            "rule_id": "60d4e5f6a7b8c9d0e1f2a3b4",
            "updated_fields": ["name", "bandwidth_limit_kbps"],
            "details": { ... updated rule details ... }
        }
    """
    if not parse_permission(config.permissions, "qos", "update"):
        logger.warning(f"Permission denied for updating QoS rule ({rule_id}).")
        return {"success": False, "error": "Permission denied to update QoS rule."}

    if not confirm:
        logger.warning(f"Confirmation missing for updating QoS rule {rule_id}.")
        return {"success": False, "error": "Confirmation required. Set 'confirm' to true."}

    if not rule_id: return {"success": False, "error": "rule_id is required"}
    if not update_data: return {"success": False, "error": "update_data cannot be empty"}

    # Validate the update data
    is_valid, error_msg, validated_data = UniFiValidatorRegistry.validate("qos_rule_update", update_data)
    if not is_valid:
        logger.warning(f"Invalid QoS rule update data for ID {rule_id}: {error_msg}")
        return {"success": False, "error": f"Invalid update data: {error_msg}"}
        
    if not validated_data:
        logger.warning(f"QoS rule update data for ID {rule_id} is empty after validation.")
        return {"success": False, "error": "Update data is effectively empty or invalid."}

    updated_fields_list = list(validated_data.keys())
    logger.info(f"Attempting to update QoS rule '{rule_id}' with fields: {', '.join(updated_fields_list)}")
    try:
        # Assuming qos_manager.update_qos_rule handles fetch-merge-put or accepts partial data
        success = await qos_manager.update_qos_rule(rule_id, validated_data)
        error_message_detail = "QoS Manager update method might need verification for partial updates."
        
        if success:
            updated_rule = await qos_manager.get_qos_rule_details(rule_id)
            logger.info(f"Successfully updated QoS rule ({rule_id})")
            return {
                "success": True,
                "rule_id": rule_id,
                "updated_fields": updated_fields_list,
                "details": json.loads(json.dumps(updated_rule, default=str))
            }
        else:
            logger.error(f"Failed to update QoS rule ({rule_id}). {error_message_detail}")
            rule_after_update = await qos_manager.get_qos_rule_details(rule_id)
            return {
                "success": False,
                "rule_id": rule_id,
                "error": f"Failed to update QoS rule ({rule_id}). Check server logs. {error_message_detail}",
                "details_after_attempt": json.loads(json.dumps(rule_after_update, default=str))
            }

    except Exception as e:
        logger.error(f"Error updating QoS rule {rule_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_create_qos_rule",
    description="Create a new QoS rule on the Unifi Network controller."
)
async def create_qos_rule(
    # Changed to accept a single data dictionary
    qos_data: Dict[str, Any] 
) -> Dict[str, Any]:
    """Creates a new Quality of Service (QoS) rule with schema validation.

    Required parameters in qos_data:
    - name (string): Descriptive name for the QoS rule.
    - interface (string): Network interface (e.g., 'WAN', 'LAN').
    - direction (string): Direction ('upload' or 'download').
    - bandwidth_limit_kbps (integer): Bandwidth limit in Kbps.
    
    Optional parameters in qos_data:
    - target_ip_address (string): Specific IP address target.
    - target_subnet (string): Subnet target (CIDR notation).
    - dscp_value (integer): DSCP value (0-63).
    - enabled (boolean): Whether the rule is enabled (default: true).
    
    Example:
    {
        "name": "Zoom Meetings High Priority",
        "interface": "WAN",
        "direction": "upload",
        "bandwidth_limit_kbps": 1000, 
        "target_subnet": "192.168.1.0/24",
        "dscp_value": 46, 
        "enabled": true
    }
    
    Returns:
    - success (boolean): Whether the operation succeeded.
    - rule_id (string): ID of the created rule if successful.
    - details (object): Details of the created rule.
    - error (string): Error message if unsuccessful.
    """
    if not parse_permission(config.permissions, "qos", "create"):
        logger.warning(f"Permission denied for creating QoS rule.")
        return {"success": False, "error": "Permission denied to create QoS rule."}

    # Validate the input data
    is_valid, error_msg, validated_data = UniFiValidatorRegistry.validate("qos_rule", qos_data)
    if not is_valid:
        logger.warning(f"Invalid QoS rule data: {error_msg}")
        return {"success": False, "error": f"Invalid data: {error_msg}"}
        
    # Basic required field check (covered by schema, but belt-and-suspenders)
    required = ["name", "interface", "direction", "bandwidth_limit_kbps"]
    if not all(k in validated_data for k in required):
        missing = [k for k in required if k not in validated_data]
        return {"success": False, "error": f"Missing required fields: {missing}"}

    rule_name = validated_data["name"]
    logger.info(f"Attempting to create QoS rule '{rule_name}'")
    try:
        # Pass validated data directly to manager
        created_rule = await qos_manager.create_qos_rule(validated_data) 

        # Check manager response
        if created_rule and created_rule.get('_id'): 
            new_rule_id = created_rule.get('_id')
            logger.info(f"Successfully created QoS rule '{rule_name}' with ID {new_rule_id}")
            return {"success": True, 
                    "site": qos_manager._connection.site, 
                    "message": f"QoS rule '{rule_name}' created successfully.", 
                    "rule_id": new_rule_id, 
                    "details": json.loads(json.dumps(created_rule, default=str))}
        else:
            error_msg = created_rule.get("error", "Manager returned failure") if isinstance(created_rule, dict) else "Manager returned non-dict or failure"
            logger.error(f"Failed to create QoS rule '{rule_name}'. Reason: {error_msg}")
            return {"success": False, "error": f"Failed to create QoS rule '{rule_name}'. {error_msg}"}
            
    except Exception as e:
        logger.error(f"Error creating QoS rule '{rule_name}': {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_create_simple_qos_rule",
    description=(
        "Create a QoS rule using a simplified high-level schema. "
        "Returns a preview unless confirm=true."
    )
)
async def create_simple_qos_rule(
    rule: Dict[str, Any],
    confirm: bool = False
) -> Dict[str, Any]:
    """Create a QoS rule with a compact schema and optional preview.

    High-level schema (validated internally):
    {
        "name": "Zoom Upload Limit",
        "interface": "wan",
        "direction": "upload",
        "limit_kbps": 2000,
        "enabled": true,             # optional – default true
        "dscp_value": 46,            # optional
        "target": {                  # optional – omit for all clients
            "type": "ip",          # "ip" | "subnet"
            "value": "192.168.1.50"
        }
    }

    If *confirm* is False (default) the function only validates and returns the
    fully-expanded UniFi payload in a preview. Set *confirm* to True to commit
    the rule and return the controller's response.
    """

    if not parse_permission(config.permissions, "qos", "create"):
        return {"success": False, "error": "Permission denied."}

    # --- Step 1: validate high-level schema --------------------------------
    is_valid, error_msg, validated = UniFiValidatorRegistry.validate("qos_rule_simple", rule)
    if not is_valid or validated is None:
        return {"success": False, "error": error_msg or "Validation failed"}

    r = validated  # alias for brevity

    # --- Step 2: translate into controller payload -------------------------
    payload: Dict[str, Any] = {
        "name": r["name"],
        "interface": r["interface"],
        "direction": r["direction"],
        "bandwidth_limit_kbps": r["limit_kbps"],
        "enabled": r.get("enabled", True),
    }

    if "dscp_value" in r:
        payload["dscp_value"] = r["dscp_value"]

    target = r.get("target")
    if target:
        t_type = target["type"].lower()
        value = target["value"]
        if t_type == "ip":
            payload["target_ip_address"] = value
        elif t_type == "subnet":
            payload["target_subnet"] = value
        else:
            return {"success": False, "error": f"Unsupported target type '{t_type}'"}

    # --- Step 3: preview or commit -----------------------------------------
    if not confirm:
        return {"success": True, "preview": payload, "message": "Set confirm=true to apply."}

    created = await qos_manager.create_qos_rule(payload)
    if created is None or not isinstance(created, dict):
        return {"success": False, "error": "Controller rejected QoS rule creation. See logs."}

    return {
        "success": True,
        "rule_id": created.get("_id"),
        "details": json.loads(json.dumps(created, default=str)),
    }