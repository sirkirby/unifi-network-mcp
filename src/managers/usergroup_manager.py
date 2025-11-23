"""User Group Manager for UniFi Network MCP server.

Manages user group operations including bandwidth limits/QoS settings per group.
"""

import logging
from typing import Dict, List, Optional, Any

from aiounifi.models.api import ApiRequest
from .connection_manager import ConnectionManager

logger = logging.getLogger("unifi-network-mcp")

CACHE_PREFIX_USERGROUPS = "usergroups"


class UserGroupManager:
    """Manages user group operations on the UniFi Controller."""

    def __init__(self, connection_manager: ConnectionManager):
        """Initialize the User Group Manager.

        Args:
            connection_manager: The shared ConnectionManager instance.
        """
        self._connection = connection_manager

    async def get_usergroups(self) -> List[Dict[str, Any]]:
        """Get all user groups for the current site.

        Returns:
            List of user group objects.
        """
        cache_key = f"{CACHE_PREFIX_USERGROUPS}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            api_request = ApiRequest(method="get", path="/rest/usergroup")
            response = await self._connection.request(api_request)

            groups = (
                response
                if isinstance(response, list)
                else response.get("data", [])
                if isinstance(response, dict)
                else []
            )

            self._connection._update_cache(cache_key, groups)
            return groups
        except Exception as e:
            logger.error(f"Error getting user groups: {e}")
            return []

    async def get_usergroup_details(
        self, group_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get details for a specific user group by ID.

        Args:
            group_id: The _id of the user group.

        Returns:
            User group object or None if not found.
        """
        try:
            all_groups = await self.get_usergroups()
            group = next(
                (g for g in all_groups if g.get("_id") == group_id), None
            )
            if not group:
                logger.debug(f"User group {group_id} not found.")
            return group
        except Exception as e:
            logger.error(f"Error getting user group details for {group_id}: {e}")
            return None

    async def get_usergroup_by_name(
        self, name: str
    ) -> Optional[Dict[str, Any]]:
        """Get a user group by its name.

        Args:
            name: The name of the user group.

        Returns:
            User group object or None if not found.
        """
        try:
            all_groups = await self.get_usergroups()
            group = next(
                (g for g in all_groups if g.get("name") == name), None
            )
            return group
        except Exception as e:
            logger.error(f"Error getting user group by name '{name}': {e}")
            return None

    async def create_usergroup(
        self,
        name: str,
        qos_rate_max_down: Optional[int] = None,
        qos_rate_max_up: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new user group with optional bandwidth limits.

        Args:
            name: Name of the user group.
            qos_rate_max_down: Download rate limit in Kbps (-1 for unlimited).
            qos_rate_max_up: Upload rate limit in Kbps (-1 for unlimited).

        Returns:
            Created user group object, or None on failure.
        """
        try:
            payload: Dict[str, Any] = {"name": name}

            if qos_rate_max_down is not None:
                payload["qos_rate_max_down"] = qos_rate_max_down
            if qos_rate_max_up is not None:
                payload["qos_rate_max_up"] = qos_rate_max_up

            api_request = ApiRequest(
                method="post",
                path="/rest/usergroup",
                data=payload,
            )
            response = await self._connection.request(api_request)

            logger.info(f"Create user group command sent: '{name}'")

            # Invalidate cache
            self._connection._invalidate_cache(
                f"{CACHE_PREFIX_USERGROUPS}_{self._connection.site}"
            )

            # Extract created group from response
            if isinstance(response, list) and len(response) > 0:
                return response[0]
            elif isinstance(response, dict):
                if "data" in response and isinstance(response["data"], list):
                    return response["data"][0] if response["data"] else None
                return response

            return None

        except Exception as e:
            logger.error(f"Error creating user group '{name}': {e}", exc_info=True)
            return None

    async def update_usergroup(
        self,
        group_id: str,
        name: Optional[str] = None,
        qos_rate_max_down: Optional[int] = None,
        qos_rate_max_up: Optional[int] = None,
    ) -> bool:
        """Update an existing user group.

        Args:
            group_id: The _id of the user group to update.
            name: New name for the group (optional).
            qos_rate_max_down: New download rate limit in Kbps (optional).
            qos_rate_max_up: New upload rate limit in Kbps (optional).

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Fetch existing group
            existing = await self.get_usergroup_details(group_id)
            if not existing:
                logger.error(f"User group {group_id} not found for update.")
                return False

            # Build update payload - merge with existing
            payload = existing.copy()

            if name is not None:
                payload["name"] = name
            if qos_rate_max_down is not None:
                payload["qos_rate_max_down"] = qos_rate_max_down
            if qos_rate_max_up is not None:
                payload["qos_rate_max_up"] = qos_rate_max_up

            api_request = ApiRequest(
                method="put",
                path=f"/rest/usergroup/{group_id}",
                data=payload,
            )
            await self._connection.request(api_request)

            logger.info(f"Update user group command sent for {group_id}")

            # Invalidate cache
            self._connection._invalidate_cache(
                f"{CACHE_PREFIX_USERGROUPS}_{self._connection.site}"
            )

            return True

        except Exception as e:
            logger.error(f"Error updating user group {group_id}: {e}", exc_info=True)
            return False

    async def delete_usergroup(self, group_id: str) -> bool:
        """Delete a user group.

        Note: Cannot delete the default user group or groups with assigned clients.

        Args:
            group_id: The _id of the user group to delete.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Verify it exists first
            existing = await self.get_usergroup_details(group_id)
            if not existing:
                logger.error(f"User group {group_id} not found for deletion.")
                return False

            # Check if it's the default group
            if existing.get("attr_no_delete"):
                logger.error(f"Cannot delete protected user group {group_id}")
                return False

            api_request = ApiRequest(
                method="delete",
                path=f"/rest/usergroup/{group_id}",
            )
            await self._connection.request(api_request)

            logger.info(f"Delete user group command sent for {group_id}")

            # Invalidate cache
            self._connection._invalidate_cache(
                f"{CACHE_PREFIX_USERGROUPS}_{self._connection.site}"
            )

            return True

        except Exception as e:
            logger.error(f"Error deleting user group {group_id}: {e}", exc_info=True)
            return False
