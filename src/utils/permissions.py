"""
Utility functions for MCP tools.
"""

import logging
from typing import Dict, Any
from collections.abc import Mapping

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
}

DEFAULT_PERMISSIONS_KEY = "default"

def parse_permission(permissions: Dict[str, Any], category: str, action: str) -> bool:
    """
    Checks if an action is permitted for a given category based on the loaded permissions.

    Args:
        permissions: The permissions dictionary (loaded from config.yaml).
        category: The category of the tool/action (e.g., "firewall", "device").
        action: The specific action (e.g., "create", "delete", "reboot").

    Returns:
        True if the action is permitted, False otherwise.
    """
    # Never allow delete operations regardless of configuration
    if action == "delete":
        logger.info(f"Delete operation requested for category '{category}'. All delete operations are disabled.")
        return False
        
    if not permissions:
        logger.warning("Permissions dictionary is empty or None. Defaulting to False.")
        return False

    # 1. Try specific category mapping
    config_category_key = CATEGORY_MAP.get(category, category) # Use mapping or category itself
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