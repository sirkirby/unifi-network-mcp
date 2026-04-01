"""Manager for MAC ACL rules (Policy Engine) on the UniFi controller.

MAC ACL rules control Layer 2 access within a VLAN by whitelisting
specific MAC address pairs that are allowed to communicate. All
traffic not explicitly allowed is blocked by a default-deny rule.

Requires UniFi Network Application with Policy Engine support.
API endpoint: /proxy/network/v2/api/site/{site}/acl-rules
"""

import logging
from typing import Any, Dict, List, Optional

from aiounifi.models.api import ApiRequestV2
from unifi_core.merge import deep_merge

from .connection_manager import ConnectionManager

logger = logging.getLogger("unifi-network-mcp")

CACHE_PREFIX_ACL_RULES = "acl_rules"


class AclManager:
    """Manages MAC ACL rules on the UniFi controller."""

    def __init__(self, connection_manager: ConnectionManager):
        self._connection = connection_manager

    async def get_acl_rules(self, network_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all MAC ACL rules, optionally filtered by network.

        Args:
            network_id: Optional network ID to filter rules by VLAN.

        Returns:
            List of ACL rule dictionaries.
        """
        cache_key = f"{CACHE_PREFIX_ACL_RULES}_{network_id}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key)
        if cached_data is not None:
            return cached_data

        if not await self._connection.ensure_connected():
            return []

        try:
            api_request = ApiRequestV2(method="get", path="/acl-rules")
            response = await self._connection.request(api_request)

            rules = (
                response
                if isinstance(response, list)
                else response.get("data", [])
                if isinstance(response, dict)
                else []
            )

            if network_id:
                rules = [r for r in rules if r.get("mac_acl_network_id") == network_id]

            self._connection._update_cache(cache_key, rules)
            return rules
        except Exception as e:
            logger.error("Error getting ACL rules: %s", e)
            return []

    async def get_acl_rule_by_id(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific ACL rule by ID.

        Args:
            rule_id: The ID of the ACL rule.

        Returns:
            The ACL rule dictionary, or None if not found.
        """
        if not await self._connection.ensure_connected():
            return None

        try:
            api_request = ApiRequestV2(method="get", path=f"/acl-rules/{rule_id}")
            response = await self._connection.request(api_request)

            if isinstance(response, list):
                return response[0] if response else None
            if isinstance(response, dict):
                return response if "_id" in response else response.get("data", None)
            return None
        except Exception as e:
            logger.error("Error getting ACL rule %s: %s", rule_id, e)
            return None

    async def create_acl_rule(self, rule_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new MAC ACL rule.

        Args:
            rule_data: Dictionary containing the ACL rule configuration.
                Required fields:
                - name (str): Rule name
                - acl_index (int): Position in the rule chain
                - action (str): "ALLOW" or "BLOCK"
                - mac_acl_network_id (str): Network ID this rule applies to
                - traffic_source (dict): Source matching config
                - traffic_destination (dict): Destination matching config
                - type (str): "MAC"

        Returns:
            The created ACL rule dictionary, or None on failure.
        """
        if not await self._connection.ensure_connected():
            return None

        required_keys = {"name", "acl_index", "action", "mac_acl_network_id", "type"}
        missing = required_keys - rule_data.keys()
        if missing:
            logger.error("Missing required keys for ACL rule: %s", missing)
            return None

        try:
            api_request = ApiRequestV2(method="post", path="/acl-rules", data=rule_data)
            response = await self._connection.request(api_request)

            self._invalidate_cache()

            if isinstance(response, dict) and "_id" in response:
                return response
            elif isinstance(response, dict) and "data" in response:
                return response["data"]
            elif isinstance(response, list) and len(response) > 0:
                return response[0] if isinstance(response[0], dict) else {"_id": str(response[0])}
            elif response is None or response == "":
                # Some API versions return empty on success — fetch the rule back
                logger.info("Create returned empty response, verifying via list")
                rules = await self.get_acl_rules()
                created = next(
                    (r for r in rules if r.get("name") == rule_data.get("name")),
                    None,
                )
                return created
            else:
                logger.error("Unexpected response creating ACL rule: %s %s", type(response), response)
                return None
        except Exception as e:
            logger.error("Error creating ACL rule: %s", e, exc_info=True)
            return None

    async def update_acl_rule(self, rule_id: str, update_data: Dict[str, Any]) -> bool:
        """Update an existing MAC ACL rule by merging updates with current state.

        Fetches the current rule, merges the caller's partial updates on top,
        and PUTs the full merged object back.

        Args:
            rule_id: The ID of the ACL rule to update.
            update_data: Dictionary of fields to update (partial is fine).

        Returns:
            True on success, False on failure.
        """
        if not await self._connection.ensure_connected():
            return False
        if not update_data:
            return True  # No action needed

        try:
            existing = await self.get_acl_rule_by_id(rule_id)
            if not existing:
                logger.error("ACL rule %s not found for update", rule_id)
                return False

            merged_data = deep_merge(existing, update_data)

            api_request = ApiRequestV2(method="put", path=f"/acl-rules/{rule_id}", data=merged_data)
            await self._connection.request(api_request)

            self._invalidate_cache()
            return True
        except Exception as e:
            logger.error("Error updating ACL rule %s: %s", rule_id, e, exc_info=True)
            return False

    async def delete_acl_rule(self, rule_id: str) -> bool:
        """Delete a MAC ACL rule.

        Args:
            rule_id: The ID of the ACL rule to delete.

        Returns:
            True on success, False on failure.
        """
        if not await self._connection.ensure_connected():
            return False

        try:
            api_request = ApiRequestV2(method="delete", path=f"/acl-rules/{rule_id}")
            await self._connection.request(api_request)

            self._invalidate_cache()
            return True
        except Exception as e:
            logger.error("Error deleting ACL rule %s: %s", rule_id, e, exc_info=True)
            return False

    def _invalidate_cache(self):
        """Invalidate all ACL rule caches."""
        self._connection._invalidate_cache(CACHE_PREFIX_ACL_RULES)
