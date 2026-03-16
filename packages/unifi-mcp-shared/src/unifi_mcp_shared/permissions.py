"""Permission checking with configurable category mappings.

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
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_PERMISSIONS_KEY = "default"


class PermissionChecker:
    """Check tool permissions against config and env vars.

    Priority order:
    1. Environment variable UNIFI_PERMISSIONS_<CATEGORY>_<ACTION>
    2. Config permissions.<category>.<action>
    3. Config permissions.default.<action>
    4. Hardcoded: read=True, everything else=False
    """

    def __init__(self, category_map: dict[str, str], permissions: dict[str, Any] | None = None):
        self.category_map = category_map
        self.permissions = permissions or {}

    def check(self, category: str, action: str) -> bool:
        """Check if an action is permitted for a given category.

        Args:
            category: The category of the tool/action (e.g., "firewall", "networks").
                      Mapped to a config key via category_map if present.
            action: The specific action (e.g., "create", "update", "delete").

        Returns:
            True if the action is permitted, False otherwise.
        """
        config_key = self.category_map.get(category, category)

        # 1. Environment variable override (highest priority)
        env_var = f"UNIFI_PERMISSIONS_{config_key.upper()}_{action.upper()}"
        env_value = os.environ.get(env_var)

        if env_value is not None:
            normalized = env_value.strip().lower()
            result = normalized in ("true", "1", "yes", "on")
            logger.info("[permissions] Env override %s=%s -> %s", env_var, env_value, result)
            return result

        # 2. Category-specific config
        cat_perms = self.permissions.get(config_key)
        if isinstance(cat_perms, Mapping):
            specific = cat_perms.get(action)
            if isinstance(specific, bool):
                logger.debug("[permissions] Config %s.%s=%s", config_key, action, specific)
                return specific

        # 3. Default section fallback
        defaults = self.permissions.get(DEFAULT_PERMISSIONS_KEY)
        if isinstance(defaults, Mapping):
            default_val = defaults.get(action)
            if isinstance(default_val, bool):
                logger.debug("[permissions] Default %s=%s", action, default_val)
                return default_val

        # 4. Hardcoded fallback: read=True, everything else=False
        if action == "read":
            logger.debug(
                "[permissions] Not explicitly configured for 'read' in category '%s'. Defaulting to allow.",
                category,
            )
            return True

        logger.warning(
            "[permissions] Not found for category '%s' (mapped to '%s') action '%s'. Denying.",
            category,
            config_key,
            action,
        )
        return False
