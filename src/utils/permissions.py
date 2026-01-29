"""
Utility functions for MCP tools.

Supports runtime permission overrides via environment variables:
- UNIFI_PERMISSIONS_<CATEGORY>_<ACTION>=true/false

Examples:
- UNIFI_PERMISSIONS_NETWORKS_CREATE=true
- UNIFI_PERMISSIONS_DEVICES_UPDATE=true
- UNIFI_PERMISSIONS_CLIENTS_UPDATE=false
"""

import logging
import os
from collections.abc import Mapping
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Mapping from tool category shorthand to config key
CATEGORY_MAP = {
    "firewall": "firewall_policies",
    "qos": "qos_rules",
    "vpn_client": "vpn_clients",
    "vpn_server": "vpn_servers",
    "vpn": "vpn",
    "network": "networks",
    "wlan": "wlans",
    "device": "devices",
    "client": "clients",
    "guest": "guests",
    "traffic_route": "traffic_routes",
    "port_forward": "port_forwards",
    "event": "events",
    "voucher": "vouchers",
    "usergroup": "usergroups",
    "route": "routes",
    "snmp": "snmp",
}

DEFAULT_PERMISSIONS_KEY = "default"


def parse_permission(permissions: Dict[str, Any], category: str, action: str) -> bool:
    """
    Checks if an action is permitted for a given category based on the loaded permissions.

    Priority order:
    1. Environment variable: UNIFI_PERMISSIONS_<CATEGORY>_<ACTION>
    2. Config file: permissions.<category>.<action>
    3. Config file: permissions.default.<action>
    4. Hardcoded default (read=true, delete=false, others=false)

    Args:
        permissions: The permissions dictionary (loaded from config.yaml).
        category: The category of the tool/action (e.g., "firewall_policies", "networks").
        action: The specific action (e.g., "create", "update", "delete").

    Returns:
        True if the action is permitted, False otherwise.

    Environment Variable Examples:
        UNIFI_PERMISSIONS_NETWORKS_CREATE=true
        UNIFI_PERMISSIONS_DEVICES_UPDATE=true
        UNIFI_PERMISSIONS_CLIENTS_UPDATE=false
    """
    # Never allow delete operations regardless of configuration
    if action == "delete":
        logger.info(f"Delete operation requested for category '{category}'. All delete operations are disabled.")
        return False

    # 0. Check environment variable override first (highest priority)
    config_category_key = CATEGORY_MAP.get(category, category)
    env_var = f"UNIFI_PERMISSIONS_{config_category_key.upper()}_{action.upper()}"
    env_value = os.getenv(env_var)

    if env_value is not None:
        # Parse environment variable (true/false/1/0/yes/no)
        normalized = env_value.strip().lower()
        is_enabled = normalized in ("true", "1", "yes", "on")
        logger.info(f"Permission override via {env_var}={env_value} -> {is_enabled}")
        return is_enabled

    if not permissions:
        logger.warning("Permissions dictionary is empty or None. Defaulting to False.")
        return False

    # 1. Try specific category mapping
    category_permissions = permissions.get(config_category_key)

    if isinstance(category_permissions, Mapping):
        # 2. Check specific action in the category
        specific_permission = category_permissions.get(action)
        if isinstance(specific_permission, bool):
            return specific_permission

    # 3. Fallback to default permissions
    default_permissions = permissions.get(DEFAULT_PERMISSIONS_KEY)
    if isinstance(default_permissions, Mapping):
        default_permission = default_permissions.get(action)
        if isinstance(default_permission, bool):
            return default_permission

    # 4. Final fallback: Deny if no specific or default found
    # Special‑case: allow read‑only actions by default when not explicitly set.
    if action == "read":
        logger.debug(
            f"Permission not explicitly configured for 'read' action in category '{category}'. Defaulting to allow."
        )
        return True

    logger.warning(
        f"Permission not found for category '{category}' (mapped to '{config_category_key}') "
        f"and action '{action}', nor in defaults. Denying action."
    )
    return False
