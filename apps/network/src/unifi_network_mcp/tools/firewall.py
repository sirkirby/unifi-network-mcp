"""
Firewall policy tools for Unifi Network MCP server.
"""

import json
import logging
from typing import Annotated, Any, Dict

from mcp.types import ToolAnnotations
from pydantic import Field

from unifi_mcp_shared.confirmation import create_preview, should_auto_confirm, toggle_preview, update_preview
from unifi_network_mcp.categories import parse_permission
from unifi_network_mcp.runtime import config, firewall_manager, network_manager, server
from unifi_network_mcp.validator_registry import UniFiValidatorRegistry  # Added

logger = logging.getLogger(__name__)


@server.tool(
    name="unifi_list_firewall_policies",
    description=(
        "List firewall policies configured on the Unifi Network controller. "
        "Includes zone-based targeting details (zone_id, matching_target, matching_target_type, "
        "IPs, network IDs) when present on newer firmware."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def list_firewall_policies(
    include_predefined: Annotated[
        bool,
        Field(
            description="When true, includes predefined system policies in results. Default false (user-defined only)"
        ),
    ] = False,
) -> Dict[str, Any]:
    """Lists firewall policies for the current UniFi site.

    Returns both legacy (ruleset-based) and zone-based policy fields.
    Zone-based fields (zone_id, matching_target, matching_target_type) are
    included in source/destination when present in the API response.
    """
    if not parse_permission(config.permissions, "firewall", "read"):
        logger.warning("Permission denied for listing firewall policies.")
        return {
            "success": False,
            "error": "Permission denied to list firewall policies.",
        }

    try:
        policies = await firewall_manager.get_firewall_policies(include_predefined=include_predefined)
        policies_raw = [p.raw if hasattr(p, "raw") else p for p in policies]

        formatted_policies = []
        for p in policies_raw:
            entry = {
                "id": p.get("_id"),
                "name": p.get("name"),
                "enabled": p.get("enabled"),
                "action": p.get("action"),
                "rule_index": p.get("index", p.get("rule_index")),
                "description": p.get("description", p.get("desc", "")),
            }
            # Include ruleset when present (legacy policies)
            if p.get("ruleset"):
                entry["ruleset"] = p["ruleset"]
            # Include zone-based source/destination targeting when present
            for direction in ("source", "destination"):
                ep = p.get(direction)
                if ep and isinstance(ep, dict):
                    targeting = {
                        "zone_id": ep.get("zone_id"),
                        "matching_target": ep.get("matching_target"),
                    }
                    if ep.get("matching_target_type"):
                        targeting["matching_target_type"] = ep["matching_target_type"]
                    if ep.get("ips"):
                        targeting["ips"] = ep["ips"]
                    if ep.get("network_ids"):
                        targeting["network_ids"] = ep["network_ids"]
                    if ep.get("client_macs"):
                        targeting["client_macs"] = ep["client_macs"]
                    entry[direction] = targeting
            formatted_policies.append(entry)

        return {
            "success": True,
            "site": firewall_manager._connection.site,
            "count": len(formatted_policies),
            "policies": formatted_policies,
        }
    except Exception as e:
        logger.error("Error listing firewall policies: %s", e, exc_info=True)
        return {"success": False, "error": "Failed to list firewall policies: %s" % e}


@server.tool(
    name="unifi_get_firewall_policy_details",
    description="Get detailed configuration for a specific firewall policy by ID.",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def get_firewall_policy_details(
    policy_id: Annotated[
        str,
        Field(description="Unique identifier (_id) of the firewall policy (from unifi_list_firewall_policies)"),
    ],
) -> Dict[str, Any]:
    """
    Gets the detailed configuration of a specific firewall policy by its ID.

    Args:
        policy_id (str): The unique identifier (_id) of the firewall policy.

    Returns:
        A dictionary containing:
        - success (bool): Indicates if the operation was successful.
        - policy_id (str): The ID of the policy requested.
        - details (Dict[str, Any]): A dictionary containing the raw configuration details
          of the firewall policy as returned by the UniFi controller.
        - error (str, optional): An error message if the operation failed (e.g., policy not found).

    Example response (success):
    {
        "success": True,
        "policy_id": "60b8a7f1e4b0f4a7f7d6e8c0",
        "details": {
            "_id": "60b8a7f1e4b0f4a7f7d6e8c0",
            "name": "Allow Established/Related",
            "enabled": True,
            "action": "accept",
            "rule_index": 2000,
            "ruleset": "WAN_IN",
            "description": "Allow established and related sessions",
            "protocol_match_excepted": False,
            "logging": False,
            "state_established": True,
            "state_invalid": False,
            "state_new": False,
            "state_related": True,
            "site_id": "...",
            # ... other fields
        }
    }
    """
    if not parse_permission(config.permissions, "firewall", "read"):
        logger.warning(f"Permission denied for getting firewall policy details ({policy_id}).")
        return {
            "success": False,
            "error": "Permission denied to get firewall policy details.",
        }

    try:
        if not policy_id:
            return {"success": False, "error": "policy_id is required"}
        policies = await firewall_manager.get_firewall_policies(include_predefined=True)
        policies_raw = [p.raw if hasattr(p, "raw") else p for p in policies]
        policy = next((p for p in policies_raw if p.get("_id") == policy_id), None)
        if not policy:
            return {
                "success": False,
                "error": f"Firewall policy with ID '{policy_id}' not found.",
            }
        return {
            "success": True,
            "policy_id": policy_id,
            "details": json.loads(json.dumps(policy, default=str)),
        }
    except Exception as e:
        logger.error(f"Error getting firewall policy details for {policy_id}: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to get firewall policy details for {policy_id}: {e}"}


@server.tool(
    name="unifi_toggle_firewall_policy",
    description="Enable or disable a specific firewall policy by ID.",
    permission_category="firewall_policies",
    permission_action="update",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
)
async def toggle_firewall_policy(
    policy_id: Annotated[
        str,
        Field(
            description="Unique identifier (_id) of the firewall policy to toggle (from unifi_list_firewall_policies)"
        ),
    ],
    confirm: Annotated[
        bool,
        Field(description="When true, executes the toggle. When false (default), returns a preview of the changes"),
    ] = False,
) -> Dict[str, Any]:
    """
    Enables or disables a specific firewall policy. Requires confirmation.

    Args:
        policy_id (str): The unique identifier (_id) of the firewall policy to toggle.
        confirm (bool): Must be explicitly set to `True` to execute the toggle operation. Defaults to `False`.

    Returns:
        A dictionary containing:
        - success (bool): Indicates if the operation was successful.
        - policy_id (str): The ID of the policy toggled.
        - enabled (bool): The new state of the policy (True if enabled, False if disabled).
        - message (str): A confirmation message indicating the action taken.
        - error (str, optional): An error message if the operation failed.

    Example response (success):
    {
        "success": True,
        "policy_id": "60b8a7f1e4b0f4a7f7d6e8c0",
        "enabled": false,
        "message": "Firewall policy 'Allow Established/Related' (60b8a7f1e4b0f4a7f7d6e8c0) toggled to disabled."
    }
    """
    if not parse_permission(config.permissions, "firewall", "update"):
        logger.warning(f"Permission denied for toggling firewall policy ({policy_id}).")
        return {
            "success": False,
            "error": "Permission denied to toggle firewall policy.",
        }

    try:
        policies = await firewall_manager.get_firewall_policies(include_predefined=True)
        policy_obj = next((p for p in policies if p.id == policy_id), None)
        if not policy_obj or not policy_obj.raw:
            return {
                "success": False,
                "error": f"Firewall policy with ID '{policy_id}' not found.",
            }
        policy = policy_obj.raw

        current_state = policy.get("enabled", False)
        policy_name = policy.get("name", policy_id)
        new_state = not current_state

        if not confirm and not should_auto_confirm():
            return toggle_preview(
                resource_type="firewall_policy",
                resource_id=policy_id,
                resource_name=policy_name,
                current_enabled=current_state,
                additional_info={
                    "action": policy.get("action"),
                    "ruleset": policy.get("ruleset"),
                    "index": policy.get("index"),
                },
            )

        logger.info(f"Attempting to toggle firewall policy '{policy_name}' ({policy_id}) to {new_state}")

        success = await firewall_manager.toggle_firewall_policy(policy_id)

        if success:
            toggled_policy_obj = next(
                (p for p in await firewall_manager.get_firewall_policies(include_predefined=True) if p.id == policy_id),
                None,
            )
            final_state = toggled_policy_obj.enabled if toggled_policy_obj else new_state

            logger.info(f"Successfully toggled firewall policy '{policy_name}' ({policy_id}) to {final_state}")
            return {
                "success": True,
                "policy_id": policy_id,
                "enabled": final_state,
                "message": f"Firewall policy '{policy_name}' ({policy_id}) toggled successfully to {'enabled' if final_state else 'disabled'}.",
            }
        else:
            logger.error(f"Failed to toggle firewall policy '{policy_name}' ({policy_id}). Manager returned false.")
            policy_after_toggle_obj = next(
                (p for p in await firewall_manager.get_firewall_policies(include_predefined=True) if p.id == policy_id),
                None,
            )
            state_after = policy_after_toggle_obj.enabled if policy_after_toggle_obj else "unknown"
            return {
                "success": False,
                "policy_id": policy_id,
                "state_after_attempt": state_after,
                "error": f"Failed to toggle firewall policy '{policy_name}' ({policy_id}). Check server logs.",
            }
    except Exception as e:
        logger.error(f"Error toggling firewall policy {policy_id}: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to toggle firewall policy {policy_id}: {e}"}


def _is_zone_based_policy(policy_data: Dict[str, Any]) -> bool:
    """Detect whether policy_data uses zone-based targeting (newer firmware).

    Zone-based policies have source/destination dicts with zone_id and no ruleset.
    Legacy policies have a ruleset field with lowercase actions.
    """
    if policy_data.get("ruleset"):
        return False
    for direction in ("source", "destination"):
        ep = policy_data.get(direction)
        if isinstance(ep, dict) and ep.get("zone_id"):
            return True
    # Uppercase actions are a zone-based indicator
    action = policy_data.get("action", "")
    if isinstance(action, str) and action in ("ALLOW", "BLOCK", "REJECT"):
        return True
    return False


def _validate_zone_targeting(validated_data: Dict[str, Any]) -> str | None:
    """Validate matching_target_type requirements for zone-based policies.

    Returns an error message string if validation fails, or None if valid.
    """
    for direction in ("source", "destination"):
        ep = validated_data.get(direction, {})
        if not isinstance(ep, dict):
            continue
        target = ep.get("matching_target")
        if target in ("IP", "NETWORK") and not ep.get("matching_target_type"):
            expected = "SPECIFIC" if target == "IP" else "OBJECT"
            return (
                "%s.matching_target_type is required when matching_target is '%s'. "
                "Use '%s'." % (direction, target, expected)
            )
        if target == "IP" and not ep.get("ips"):
            return "%s.ips array is required when matching_target is 'IP'." % direction
        if target == "NETWORK" and not ep.get("network_ids"):
            return "%s.network_ids array is required when matching_target is 'NETWORK'." % direction
    return None


@server.tool(
    name="unifi_create_firewall_policy",
    description=(
        "Create a new firewall policy with schema validation. Supports both legacy "
        "ruleset-based policies (action: accept/drop/reject) and zone-based policies "
        "(action: ALLOW/BLOCK/REJECT with source/destination zone_id targeting). "
        "Format is auto-detected from the policy_data structure."
    ),
    permission_category="firewall_policies",
    permission_action="create",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
)
async def create_firewall_policy(
    policy_data: Annotated[
        Dict[str, Any],
        Field(
            description=(
                "Firewall policy configuration dict. Two formats supported:\n"
                "Legacy (ruleset-based): Required: name, ruleset (WAN_IN, LAN_OUT, etc.), "
                "action (accept/drop/reject), index. Optional: enabled, description, protocol, "
                "connection_states, source, destination, logging.\n"
                "Zone-based (firmware 5.0+): Required: name, action (ALLOW/BLOCK/REJECT), "
                "source (object with zone_id, matching_target), destination (same structure). "
                "For IP targeting: matching_target='IP', matching_target_type='SPECIFIC', ips=[...]. "
                "For network targeting: matching_target='NETWORK', matching_target_type='OBJECT', "
                "network_ids=[...]. For any in zone: matching_target='ANY'."
            )
        ),
    ],
    confirm: Annotated[
        bool,
        Field(description="When true, creates the policy. When false (default), validates and returns a preview"),
    ] = False,
) -> Dict[str, Any]:
    """Create a firewall policy. Auto-detects legacy vs zone-based format."""
    if not parse_permission(config.permissions, "firewall", "create"):
        logger.warning("Permission denied for creating firewall policy.")
        return {
            "success": False,
            "error": "Permission denied to create firewall policy.",
        }

    if not isinstance(policy_data, dict) or not policy_data:
        return {
            "success": False,
            "error": "policy_data must be a non-empty dictionary.",
        }

    # Auto-detect format and validate accordingly
    zone_based = _is_zone_based_policy(policy_data)

    if zone_based:
        schema_key = "firewall_policy_v2_create"
    else:
        schema_key = "firewall_policy_create"

    is_valid, error_msg, validated_data = UniFiValidatorRegistry.validate(schema_key, policy_data)

    if not is_valid:
        logger.warning("Invalid firewall policy data: %s", error_msg)
        return {"success": False, "error": "Validation Error: %s" % error_msg}

    if zone_based:
        # Validate zone targeting requirements (matching_target_type, ips, network_ids)
        targeting_error = _validate_zone_targeting(validated_data)
        if targeting_error:
            return {"success": False, "error": targeting_error}
        # Normalize action to uppercase
        action = validated_data.get("action", "")
        if action.upper() not in ("ALLOW", "BLOCK", "REJECT"):
            return {"success": False, "error": "Invalid action '%s'. Must be ALLOW, BLOCK, or REJECT." % action}
        validated_data["action"] = action.upper()
    else:
        # Normalize action to lowercase for legacy format
        action = validated_data.get("action", "")
        if not isinstance(action, str) or action.lower() not in ("accept", "drop", "reject"):
            return {
                "success": False,
                "error": "Invalid action '%s'. Must be one of 'accept', 'drop', 'reject'." % action,
            }
        validated_data["action"] = action.lower()

    policy_name = validated_data.get("name", "Unnamed Policy")

    if not confirm and not should_auto_confirm():
        return create_preview(
            resource_type="firewall_policy",
            resource_data=validated_data,
            resource_name=policy_name,
        )

    logger.info("Creating firewall policy '%s'", policy_name)

    try:
        created_policy_obj = await firewall_manager.create_firewall_policy(validated_data)

        if created_policy_obj and hasattr(created_policy_obj, "raw"):
            created_policy_details = created_policy_obj.raw
            new_policy_id = created_policy_details.get("_id", "unknown")
            logger.info("Created firewall policy '%s' with ID %s", policy_name, new_policy_id)
            return {
                "success": True,
                "message": "Firewall policy '%s' created successfully." % policy_name,
                "policy_id": new_policy_id,
                "details": json.loads(json.dumps(created_policy_details, default=str)),
            }
        else:
            logger.error("Failed to create firewall policy '%s'. Manager returned None.", policy_name)
            return {
                "success": False,
                "error": "Failed to create firewall policy '%s'. Check server logs." % policy_name,
            }

    except Exception as e:
        logger.error("Error creating firewall policy '%s': %s", policy_name, e, exc_info=True)
        return {"success": False, "error": "Failed to create firewall policy '%s': %s" % (policy_name, e)}


# Fields that indicate zone-based update data (not in the legacy update schema)
_V2_UPDATE_FIELDS = frozenset({
    "source", "destination", "ip_version", "connection_state_type", "connection_states",
    "create_allow_respond", "match_ip_sec", "match_opposite_protocol", "schedule",
    "icmp_typename", "icmp_v6_typename",
})


@server.tool(
    name="unifi_update_firewall_policy",
    description=(
        "Update specific fields of an existing firewall policy by ID. Supports both "
        "legacy fields (ruleset, action as accept/drop/reject) and zone-based fields "
        "(source, destination, action as ALLOW/BLOCK/REJECT, ip_version, etc.)."
    ),
    permission_category="firewall_policies",
    permission_action="update",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
)
async def update_firewall_policy(
    policy_id: Annotated[
        str,
        Field(
            description="Unique identifier (_id) of the firewall policy to update (from unifi_list_firewall_policies)"
        ),
    ],
    update_data: Annotated[
        Dict[str, Any],
        Field(
            description=(
                "Dictionary of fields to update. Accepts both legacy and zone-based fields. "
                "Legacy: name, ruleset, action (accept/drop/reject), rule_index, protocol, "
                "src_address, dst_address, enabled, description, logging. "
                "Zone-based: name, action (ALLOW/BLOCK/REJECT), enabled, source, destination, "
                "protocol, ip_version, index, logging, connection_state_type, connection_states, schedule."
            )
        ),
    ],
    confirm: Annotated[
        bool,
        Field(description="When true, applies the update. When false (default), returns a preview of the changes"),
    ] = False,
) -> Dict[str, Any]:
    """Update specific fields of an existing firewall policy. Requires confirmation."""
    if not parse_permission(config.permissions, "firewall", "update"):
        logger.warning("Permission denied for updating firewall policy (%s).", policy_id)
        return {
            "success": False,
            "error": "Permission denied to update firewall policy.",
        }

    if not policy_id:
        return {"success": False, "error": "policy_id is required"}
    if not update_data:
        return {"success": False, "error": "update_data cannot be empty"}

    # Normalize action if provided (accept both cases)
    if "action" in update_data:
        action = update_data["action"]
        if isinstance(action, str):
            upper = action.upper()
            lower = action.lower()
            if upper in ("ALLOW", "BLOCK", "REJECT"):
                update_data["action"] = upper
            elif lower in ("accept", "drop", "reject"):
                update_data["action"] = lower
            else:
                return {"success": False, "error": "Invalid action '%s'." % action}

    # Detect whether this contains zone-based fields
    has_v2_fields = bool(set(update_data.keys()) & _V2_UPDATE_FIELDS)

    if has_v2_fields:
        # Skip legacy schema validation for zone-based updates; the manager
        # merges fields into the existing policy and sends the full payload.
        validated_data = update_data
    else:
        is_valid, error_msg, validated_data = UniFiValidatorRegistry.validate("firewall_policy_update", update_data)
        if not is_valid:
            logger.warning("Invalid firewall policy update data for ID %s: %s", policy_id, error_msg)
            return {"success": False, "error": "Invalid update data: %s" % error_msg}
        if not validated_data:
            return {"success": False, "error": "Update data is effectively empty or invalid."}

    updated_fields_list = list(validated_data.keys())

    try:
        policies = await firewall_manager.get_firewall_policies(include_predefined=True)
        current_policy_obj = next((p for p in policies if p.id == policy_id), None)
        if not current_policy_obj or not current_policy_obj.raw:
            return {
                "success": False,
                "error": "Firewall policy with ID '%s' not found." % policy_id,
            }
        current = current_policy_obj.raw

        if not confirm and not should_auto_confirm():
            return update_preview(
                resource_type="firewall_policy",
                resource_id=policy_id,
                resource_name=current.get("name"),
                current_state=current,
                updates=validated_data,
            )

        logger.info("Updating firewall policy '%s' fields: %s", policy_id, ", ".join(updated_fields_list))

        success = await firewall_manager.update_firewall_policy(policy_id, validated_data)

        if success:
            updated_policy_obj = next(
                (p for p in await firewall_manager.get_firewall_policies(include_predefined=True) if p.id == policy_id),
                None,
            )
            updated_details = updated_policy_obj.raw if updated_policy_obj else {}
            logger.info("Updated firewall policy (%s)", policy_id)
            return {
                "success": True,
                "policy_id": policy_id,
                "updated_fields": updated_fields_list,
                "details": json.loads(json.dumps(updated_details, default=str)),
            }
        else:
            logger.error("Failed to update firewall policy (%s). Manager returned false.", policy_id)
            return {
                "success": False,
                "policy_id": policy_id,
                "error": "Failed to update firewall policy (%s). Check server logs." % policy_id,
            }

    except Exception as e:
        logger.error("Error updating firewall policy %s: %s", policy_id, e, exc_info=True)
        return {"success": False, "error": "Failed to update firewall policy %s: %s" % (policy_id, e)}


@server.tool(
    name="unifi_create_simple_firewall_policy",
    description=(
        "Create a firewall policy using a simplified high-level schema. "
        "Accepts friendly src/dst selectors and returns a preview unless confirm=true."
    ),
    permission_category="firewall_policies",
    permission_action="create",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
)
async def create_simple_firewall_policy(
    policy: Annotated[
        Dict[str, Any],
        Field(
            description="Simplified firewall policy dict. Required: name (str), ruleset (str: 'LAN_OUT', 'WAN_IN', etc.), action (str: 'drop', 'accept', 'reject'), src (dict with type+value), dst (dict with type+value). src/dst type options: 'zone' (value: 'wan'/'lan'), 'network' (value: network name/ID), 'client_mac' (value: MAC address), 'ip_group' (value: group ID). Optional: protocol, index, enabled, log"
        ),
    ],
    confirm: Annotated[
        bool,
        Field(description="When true, creates the policy. When false (default), validates and returns a preview"),
    ] = False,
) -> Dict[str, Any]:
    """Create a firewall rule with a compact schema and optional preview.

    High-level schema (validated internally):
    {
        "name":    "Block Xbox",
        "ruleset": "LAN_OUT",
        "action":  "drop",
        "src": {"type": "client_mac", "value": "4c:3b:df:2c:c8:c6"},
        "dst": {"type": "zone", "value": "wan"},
        "protocol": "all",           # optional
        "index": 2010,                # optional – will auto-place if omitted
        "enabled": true,              # default true
        "log": true                   # default false
    }

    If *confirm* is False (default) the function only validates and returns the
    fully-expanded UniFi payload in a preview. Set *confirm* to True to commit
    the rule and return the controller's response.
    """

    if not parse_permission(config.permissions, "firewall", "create"):
        return {"success": False, "error": "Permission denied."}

    # --- Step 1: validate high-level schema --------------------------------
    is_valid, error, validated = UniFiValidatorRegistry.validate("firewall_policy_simple", policy)
    if not is_valid or validated is None:
        return {"success": False, "error": error or "Validation failed"}

    pol = validated  # rename for brevity

    # --- Step 2: translate src/dst selectors into UniFi endpoint structure --
    async def _resolve_endpoint(ep: Dict[str, str]) -> Dict[str, Any]:
        etype = ep["type"].lower()
        value = ep["value"].strip()
        base = {
            "match_opposite_ports": False,
            "port_matching_type": "any",
        }
        if etype == "zone":
            return {**base, "matching_target": "zone", "zone_id": value.lower()}
        if etype == "network":
            # Accept network name or id
            networks = await network_manager.get_networks()
            net = next(
                (n for n in networks if n.get("_id") == value or n.get("name") == value),
                None,
            )
            if not net:
                raise ValueError(f"Network '{value}' not found")
            return {
                **base,
                "matching_target": "network_id",
                "network_id": net["_id"],
                "zone_id": "lan",  # network selectors still need zone for API; default lan
            }
        if etype == "client_mac":
            return {
                **base,
                "matching_target": "client_macs",
                "client_macs": [value.lower()],
                "zone_id": "lan",
            }
        if etype == "ip_group":
            return {
                **base,
                "matching_target": "ip_group_id",
                "ip_group_id": value,
                "zone_id": "lan",
            }
        raise ValueError(f"Unsupported selector type '{etype}'")

    try:
        src_ep = await _resolve_endpoint(pol["src"])
        dst_ep = await _resolve_endpoint(pol["dst"])
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    # --- Step 3: build controller payload ----------------------------------
    payload: Dict[str, Any] = {
        "name": pol["name"],
        "ruleset": pol["ruleset"],
        "action": pol["action"].lower(),
        "index": pol.get("index", 3000),  # fall-back index
        "enabled": pol.get("enabled", True),
        "logging": pol.get("log", False),
        "protocol": pol.get("protocol", "all"),
        # sane defaults for connection states (inclusive all)
        "connection_state_type": "inclusive",
        "connection_states": ["new", "established", "related", "invalid"],
        "source": src_ep,
        "destination": dst_ep,
    }

    if not confirm and not should_auto_confirm():
        return create_preview(
            resource_type="firewall_policy",
            resource_data=payload,
            resource_name=pol["name"],
        )

    # --- Step 4: call manager to create policy -----------------------------
    created = await firewall_manager.create_firewall_policy(payload)
    if created is None:
        return {
            "success": False,
            "error": "Controller rejected policy creation. See logs.",
        }

    return {
        "success": True,
        "policy_id": created.id,
        "details": created.raw,
    }


@server.tool(
    name="unifi_list_firewall_zones",
    description="List controller firewall zones (V2 API).",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def list_firewall_zones() -> Dict[str, Any]:
    zones = await firewall_manager.get_firewall_zones()
    return {"success": True, "count": len(zones), "zones": zones}


@server.tool(
    name="unifi_list_ip_groups",
    description="List IP groups configured on the controller (V2 API).",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def list_ip_groups() -> Dict[str, Any]:
    groups = await firewall_manager.get_ip_groups()
    return {"success": True, "count": len(groups), "ip_groups": groups}


@server.tool(
    name="unifi_delete_firewall_policy",
    description=(
        "Delete a firewall policy by ID. Requires confirmation. "
        "WARNING: Removing an ALLOW rule may block traffic. Removing a BLOCK rule may open access."
    ),
    permission_category="firewall_policies",
    permission_action="delete",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=False),
)
async def delete_firewall_policy(
    policy_id: Annotated[
        str,
        Field(
            description="Unique identifier (_id) of the firewall policy to delete (from unifi_list_firewall_policies)"
        ),
    ],
    confirm: Annotated[
        bool,
        Field(
            description="When true, deletes the policy. When false (default), returns a preview. "
            "WARNING: Removing an ALLOW rule may block traffic"
        ),
    ] = False,
) -> Dict[str, Any]:
    """Delete a firewall policy by ID."""
    if not parse_permission(config.permissions, "firewall", "delete"):
        return {"success": False, "error": "Permission denied to delete firewall policy."}

    if not confirm and not should_auto_confirm():
        return create_preview(
            resource_type="firewall_policy",
            resource_data={"policy_id": policy_id},
            resource_name=policy_id,
            warnings=["Removing an ALLOW rule may block traffic. Removing a BLOCK rule may open access."],
        )

    try:
        success = await firewall_manager.delete_firewall_policy(policy_id)
        if success:
            return {"success": True, "message": "Firewall policy '%s' deleted successfully." % policy_id}
        return {"success": False, "error": "Failed to delete firewall policy '%s'." % policy_id}
    except Exception as e:
        logger.error("Error deleting firewall policy %s: %s", policy_id, e, exc_info=True)
        return {"success": False, "error": "Failed to delete firewall policy %s: %s" % (policy_id, e)}
