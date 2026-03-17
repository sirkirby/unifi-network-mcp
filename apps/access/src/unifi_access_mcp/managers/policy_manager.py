"""Policy management for UniFi Access.

Provides methods to query and manage access policies and schedules
via the Access controller API.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from unifi_access_mcp.managers.connection_manager import AccessConnectionManager

logger = logging.getLogger(__name__)


class PolicyManager:
    """Reads and mutates access policy data from the Access controller."""

    def __init__(self, connection_manager: AccessConnectionManager) -> None:
        self._cm = connection_manager

    # ------------------------------------------------------------------
    # Read-only methods (stubs)
    # ------------------------------------------------------------------

    async def list_policies(self) -> List[Dict[str, Any]]:
        """Return all access policies as summary dicts."""
        raise NotImplementedError("PolicyManager.list_policies not yet implemented")

    async def get_policy(self, policy_id: str) -> Dict[str, Any]:
        """Return detailed information for a single access policy."""
        raise NotImplementedError("PolicyManager.get_policy not yet implemented")

    async def list_schedules(self) -> List[Dict[str, Any]]:
        """Return all access schedules."""
        raise NotImplementedError("PolicyManager.list_schedules not yet implemented")
