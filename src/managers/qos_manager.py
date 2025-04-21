import logging
from typing import Dict, List, Optional, Any

from aiounifi.models.api import ApiRequest, ApiRequestV2
from .connection_manager import ConnectionManager

logger = logging.getLogger("unifi-network-mcp")

CACHE_PREFIX_QOS = "qos_rules"

class QosManager:
    """Manages QoS (Quality of Service) rules on the Unifi Controller."""

    def __init__(self, connection_manager: ConnectionManager):
        """Initialize the QoS Manager.

        Args:
            connection_manager: The shared ConnectionManager instance.
        """
        self._connection = connection_manager

    async def get_qos_rules(self) -> List[Dict[str, Any]]:
        """Get QoS rules for the current site."""
        cache_key = f"{CACHE_PREFIX_QOS}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            api_request = ApiRequestV2(method="get", path="/qos-rules")
            response = await self._connection.request(api_request)
            rules = response if isinstance(response, list) else response.get('data', []) if isinstance(response, dict) else []
            self._connection._update_cache(cache_key, rules)
            return rules
        except Exception as e:
            logger.error(f"Error getting QoS rules: {e}")
            return []

    async def get_qos_rule_details(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific QoS rule."""
        try:
            all_rules = await self.get_qos_rules()
            rule = next((r for r in all_rules if r.get("_id") == rule_id), None)
            if not rule:
                logger.warning(f"QoS rule {rule_id} not found in fetched list.")
            return rule
        except Exception as e:
            logger.error(f"Error getting QoS rule details for {rule_id}: {e}", exc_info=True)
            return None

    async def update_qos_rule(self, rule_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a QoS rule by merging updates with existing data.

        Args:
            rule_id: ID of the rule to update
            update_data: Dictionary of fields to update

        Returns:
            bool: True if successful, False otherwise
        """
        if not await self._connection.ensure_connected():
            return False
        if not update_data:
            logger.warning(f"No update data provided for QoS rule {rule_id}.")
            return True # No action needed
            
        try:
            # 1. Fetch existing rule data
            existing_rule = await self.get_qos_rule_details(rule_id)
            if not existing_rule:
                logger.error(f"QoS rule {rule_id} not found for update.")
                return False
                
            # 2. Merge updates into existing data
            merged_data = existing_rule.copy()
            for key, value in update_data.items():
                merged_data[key] = value
                
            # 3. Send the full merged data using V2 PUT
            api_request = ApiRequestV2(
                method="put",
                path=f"/qos-rules/{rule_id}",
                data=merged_data # Send full merged object
            )
            await self._connection.request(api_request)
            logger.info(f"Update command sent for QoS rule {rule_id} with merged data.")
            self._connection._invalidate_cache(f"{CACHE_PREFIX_QOS}_{self._connection.site}")
            return True
        except Exception as e:
            logger.error(f"Error updating QoS rule {rule_id}: {e}", exc_info=True)
            return False

    async def create_qos_rule(self, rule_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new QoS rule.

        Args:
            rule_data: Dictionary with rule data

        Returns:
            The created rule data if successful, None otherwise
        """
        try:
            required_fields = ["name", "enabled"]
            for field in required_fields:
                if field not in rule_data:
                    logger.error(f"Missing required field '{field}' for QoS rule creation")
                    return None

            api_request = ApiRequestV2(
                method="post",
                path="/qos-rules",
                data=rule_data
            )
            response = await self._connection.request(api_request)
            logger.info(f"Create command sent for QoS rule '{rule_data.get('name')}'")
            self._connection._invalidate_cache(f"{CACHE_PREFIX_QOS}_{self._connection.site}")

            if isinstance(response, dict) and "data" in response and isinstance(response["data"], list) and len(response["data"]) > 0:
                return response["data"][0]
            elif isinstance(response, list) and len(response) > 0 and isinstance(response[0], dict): # Handle cases where API returns a list
                 return response[0]
            logger.warning(f"Could not extract created QoS rule data from response: {response}")
            return response # Return raw response if extraction fails

        except Exception as e:
            logger.error(f"Error creating QoS rule: {e}")
            return None

    async def delete_qos_rule(self, rule_id: str) -> bool:
        """Delete a QoS rule.

        Args:
            rule_id: ID of the rule to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            api_request = ApiRequestV2(
                method="delete",
                path=f"/qos-rules/{rule_id}"
            )
            await self._connection.request(api_request)
            logger.info(f"Delete command sent for QoS rule {rule_id}")
            self._connection._invalidate_cache(f"{CACHE_PREFIX_QOS}_{self._connection.site}")
            return True
        except Exception as e:
            logger.error(f"Error deleting QoS rule {rule_id}: {e}")
            return False 