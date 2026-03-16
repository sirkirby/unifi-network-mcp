"""Usergroup Manager for UniFi Network MCP server.

Manages user group operations for bandwidth limits and client categorization.
"""

import logging
from typing import Any, Dict, List, Optional

from aiounifi.models.api import ApiRequest

from .connection_manager import ConnectionManager

logger = logging.getLogger("unifi-network-mcp")

CACHE_PREFIX_USERGROUPS = "usergroups"


class UsergroupManager:
    """Manages user group operations on the UniFi Controller."""

    def __init__(self, connection_manager: ConnectionManager):
        """Initialize the Usergroup Manager.

        Args:
            connection_manager: The shared ConnectionManager instance.
        """
        self._connection = connection_manager

    async def get_usergroups(self) -> List[Dict[str, Any]]:
        """Get all user groups for the current site.

        Uses GET /rest/usergroup endpoint.

        Returns:
            List of user group objects containing name, bandwidth limits, etc.
        """
        cache_key = f"{CACHE_PREFIX_USERGROUPS}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            api_request = ApiRequest(method="get", path="/rest/usergroup")
            response = await self._connection.request(api_request)

            usergroups = (
                response
                if isinstance(response, list)
                else response.get("data", [])
                if isinstance(response, dict)
                else []
            )

            self._connection._update_cache(cache_key, usergroups)
            return usergroups
        except Exception as e:
            logger.error(f"Error getting user groups: {e}")
            return []

    async def get_usergroup_details(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific user group by ID.

        Args:
            group_id: The _id of the user group.

        Returns:
            User group object or None if not found.
        """
        try:
            all_groups = await self.get_usergroups()
            group = next((g for g in all_groups if g.get("_id") == group_id), None)
            if not group:
                logger.debug(f"User group {group_id} not found.")
            return group
        except Exception as e:
            logger.error(f"Error getting user group details for {group_id}: {e}")
            return None

    async def create_usergroup(
        self,
        name: str,
        down_limit_kbps: Optional[int] = None,
        up_limit_kbps: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new user group with optional bandwidth limits.

        Uses POST to /rest/usergroup endpoint.

        Args:
            name: Name for the user group.
            down_limit_kbps: Optional download speed limit in Kbps (-1 for unlimited).
            up_limit_kbps: Optional upload speed limit in Kbps (-1 for unlimited).

        Returns:
            Created user group object, or None on failure.
        """
        try:
            payload: Dict[str, Any] = {"name": name}

            # -1 means unlimited in UniFi API
            if down_limit_kbps is not None:
                payload["qos_rate_max_down"] = down_limit_kbps
            if up_limit_kbps is not None:
                payload["qos_rate_max_up"] = up_limit_kbps

            api_request = ApiRequest(
                method="post",
                path="/rest/usergroup",
                data=payload,
            )
            response = await self._connection.request(api_request)

            logger.info(f"Created user group: {name}")

            # Invalidate cache
            self._connection._invalidate_cache(f"{CACHE_PREFIX_USERGROUPS}_{self._connection.site}")

            # Return the created group
            if isinstance(response, list) and len(response) > 0:
                return response[0]
            elif isinstance(response, dict):
                return response.get("data", [response])[0] if response else None

            return None

        except Exception as e:
            logger.error(f"Error creating user group: {e}", exc_info=True)
            return None

    async def update_usergroup(
        self,
        group_id: str,
        name: Optional[str] = None,
        down_limit_kbps: Optional[int] = None,
        up_limit_kbps: Optional[int] = None,
    ) -> bool:
        """Update an existing user group.

        Uses PUT to /rest/usergroup/{group_id} endpoint.

        Args:
            group_id: The _id of the user group to update.
            name: Optional new name for the group.
            down_limit_kbps: Optional new download limit in Kbps (-1 for unlimited).
            up_limit_kbps: Optional new upload limit in Kbps (-1 for unlimited).

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Get current group data first
            current = await self.get_usergroup_details(group_id)
            if not current:
                logger.error(f"User group {group_id} not found for update.")
                return False

            # Build payload with updates
            payload: Dict[str, Any] = {}
            if name is not None:
                payload["name"] = name
            if down_limit_kbps is not None:
                payload["qos_rate_max_down"] = down_limit_kbps
            if up_limit_kbps is not None:
                payload["qos_rate_max_up"] = up_limit_kbps

            if not payload:
                logger.warning(f"No updates provided for user group {group_id}")
                return False

            api_request = ApiRequest(
                method="put",
                path=f"/rest/usergroup/{group_id}",
                data=payload,
            )
            await self._connection.request(api_request)

            logger.info(f"Updated user group {group_id}: {payload}")

            # Invalidate cache
            self._connection._invalidate_cache(f"{CACHE_PREFIX_USERGROUPS}_{self._connection.site}")

            return True

        except Exception as e:
            logger.error(f"Error updating user group {group_id}: {e}", exc_info=True)
            return False
