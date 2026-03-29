"""Manager for OON (Object-Oriented Network) policies on the UniFi controller.

OON policies provide high-level network access control including:
- Internet access scheduling (bedtime blackouts)
- Application blocking (social media, streaming)
- QoS/bandwidth limiting
- Policy-based routing (VPN steering)

Policies can target specific client MACs or client groups.

API endpoints:
  LIST:   GET  /proxy/network/v2/api/site/{site}/object-oriented-network-configs  (plural)
  GET:    GET  /proxy/network/v2/api/site/{site}/object-oriented-network-config/{id}  (singular)
  CREATE: POST /proxy/network/v2/api/site/{site}/object-oriented-network-config  (singular)
  UPDATE: PUT  /proxy/network/v2/api/site/{site}/object-oriented-network-config/{id}  (singular)
  DELETE: DELETE /proxy/network/v2/api/site/{site}/object-oriented-network-config/{id}  (singular)

Note: The list endpoint uses the PLURAL form, while all other operations use SINGULAR.
"""

import logging
from typing import Any, Dict, List, Optional

from aiounifi.models.api import ApiRequestV2

from .connection_manager import ConnectionManager

logger = logging.getLogger("unifi-network-mcp")

CACHE_PREFIX_OON_POLICIES = "oon_policies"

# Asymmetric paths: list uses plural, CRUD uses singular
OON_PATH_LIST = "/object-oriented-network-configs"
OON_PATH_SINGLE = "/object-oriented-network-config"


class OonManager:
    """Manages OON (Object-Oriented Network) policies on the UniFi controller."""

    def __init__(self, connection_manager: ConnectionManager):
        self._connection = connection_manager

    async def get_oon_policies(self) -> List[Dict[str, Any]]:
        """Get all OON policies.

        Returns:
            List of OON policy dictionaries.
        """
        cache_key = f"{CACHE_PREFIX_OON_POLICIES}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key)
        if cached_data is not None:
            return cached_data

        if not await self._connection.ensure_connected():
            return []

        try:
            api_request = ApiRequestV2(method="get", path=OON_PATH_LIST)
            response = await self._connection.request(api_request)

            policies = (
                response
                if isinstance(response, list)
                else response.get("data", [])
                if isinstance(response, dict)
                else []
            )

            self._connection._update_cache(cache_key, policies)
            return policies
        except Exception as e:
            error_str = str(e).lower()
            if "404" in error_str or "not found" in error_str:
                logger.debug("OON policies not available (controller may not support them): %s", e)
                return []
            logger.error("Error getting OON policies: %s", e)
            return []

    async def get_oon_policy_by_id(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific OON policy by ID.

        Args:
            policy_id: The ID of the OON policy.

        Returns:
            The OON policy dictionary, or None if not found.
        """
        if not await self._connection.ensure_connected():
            return None

        try:
            api_request = ApiRequestV2(method="get", path=f"{OON_PATH_SINGLE}/{policy_id}")
            response = await self._connection.request(api_request)

            if isinstance(response, list) and response:
                return response[0]
            if isinstance(response, dict):
                result = response if ("id" in response or "_id" in response) else response.get("data", None)
                if result:
                    return result

            # Fallback: search in list
            policies = await self.get_oon_policies()
            return next((p for p in policies if p.get("id", p.get("_id")) == policy_id), None)
        except Exception as e:
            logger.error("Error getting OON policy %s: %s", policy_id, e)
            return None

    async def create_oon_policy(self, policy_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new OON policy.

        Args:
            policy_data: Dictionary containing the policy configuration.
                Required fields:
                - name (str): Policy name
                - enabled (bool): Whether the policy is active
                - target_type (str): "CLIENTS" or "GROUPS"
                - targets (list): MAC addresses or group IDs
                At least one of secure, qos, or route must be configured.

        Returns:
            The created OON policy dictionary, or None on failure.
        """
        if not await self._connection.ensure_connected():
            return None

        if not policy_data.get("name"):
            logger.error("Missing required field 'name' for OON policy")
            return None

        # Strip _id/id if present — let the API assign a new one
        create_data = policy_data.copy()
        create_data.pop("_id", None)
        create_data.pop("id", None)

        try:
            # POST uses singular path, may return 201
            api_request = ApiRequestV2(method="post", path=OON_PATH_SINGLE, data=create_data)
            response = await self._connection.request(api_request)

            self._invalidate_cache()

            if isinstance(response, dict) and ("id" in response or "_id" in response):
                return response
            elif isinstance(response, dict) and "data" in response:
                data = response["data"]
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
                return data
            elif isinstance(response, list) and len(response) > 0:
                return response[0] if isinstance(response[0], dict) else {"id": str(response[0])}
            elif response is None or response == "":
                logger.info("Create returned empty response, verifying via list")
                policies = await self.get_oon_policies()
                created = next(
                    (p for p in policies if p.get("name") == policy_data.get("name")),
                    None,
                )
                return created
            else:
                logger.error("Unexpected response creating OON policy: %s %s", type(response), response)
                return None
        except Exception as e:
            logger.error("Error creating OON policy: %s", e, exc_info=True)
            return None

    async def update_oon_policy(self, policy_id: str, update_data: Dict[str, Any]) -> bool:
        """Update an existing OON policy by merging updates with current state.

        Args:
            policy_id: The ID of the OON policy to update.
            update_data: Dictionary of fields to update (partial is fine).

        Returns:
            True on success, False on failure.
        """
        if not await self._connection.ensure_connected():
            return False
        if not update_data:
            return True

        try:
            existing = await self.get_oon_policy_by_id(policy_id)
            if not existing:
                logger.error("OON policy %s not found for update", policy_id)
                return False

            merged_data = existing.copy()
            for key, value in update_data.items():
                merged_data[key] = value

            api_request = ApiRequestV2(method="put", path=f"{OON_PATH_SINGLE}/{policy_id}", data=merged_data)
            await self._connection.request(api_request)

            self._invalidate_cache()
            return True
        except Exception as e:
            logger.error("Error updating OON policy %s: %s", policy_id, e, exc_info=True)
            return False

    async def toggle_oon_policy(self, policy_id: str) -> Optional[bool]:
        """Toggle an OON policy's enabled state.

        Fetches the current policy, flips the enabled flag, and sends
        the full object back via PUT.

        Args:
            policy_id: The ID of the OON policy to toggle.

        Returns:
            The new enabled state (True/False), or None on failure.
        """
        if not await self._connection.ensure_connected():
            return None

        try:
            policy = await self.get_oon_policy_by_id(policy_id)
            if not policy:
                logger.error("OON policy %s not found for toggle", policy_id)
                return None

            new_state = not policy.get("enabled", False)
            policy["enabled"] = new_state

            api_request = ApiRequestV2(method="put", path=f"{OON_PATH_SINGLE}/{policy_id}", data=policy)
            await self._connection.request(api_request)

            self._invalidate_cache()
            return new_state
        except Exception as e:
            logger.error("Error toggling OON policy %s: %s", policy_id, e, exc_info=True)
            return None

    async def delete_oon_policy(self, policy_id: str) -> bool:
        """Delete an OON policy.

        Args:
            policy_id: The ID of the OON policy to delete.

        Returns:
            True on success, False on failure.
        """
        if not await self._connection.ensure_connected():
            return False

        try:
            # DELETE may return 204 No Content
            api_request = ApiRequestV2(method="delete", path=f"{OON_PATH_SINGLE}/{policy_id}")
            await self._connection.request(api_request)

            self._invalidate_cache()
            return True
        except Exception as e:
            logger.error("Error deleting OON policy %s: %s", policy_id, e, exc_info=True)
            return False

    def _invalidate_cache(self):
        """Invalidate all OON policy caches."""
        self._connection._invalidate_cache(CACHE_PREFIX_OON_POLICIES)
