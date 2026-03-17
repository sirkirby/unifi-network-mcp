"""Door management for UniFi Access.

Provides methods to query door state, lock/unlock doors, and manage
door configurations via the Access controller API.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from unifi_access_mcp.managers.connection_manager import AccessConnectionManager

logger = logging.getLogger(__name__)


class DoorManager:
    """Reads and mutates door data from the Access controller."""

    def __init__(self, connection_manager: AccessConnectionManager) -> None:
        self._cm = connection_manager

    # ------------------------------------------------------------------
    # Read-only methods (stubs)
    # ------------------------------------------------------------------

    async def list_doors(self) -> List[Dict[str, Any]]:
        """Return all doors as summary dicts."""
        raise NotImplementedError("DoorManager.list_doors not yet implemented")

    async def get_door(self, door_id: str) -> Dict[str, Any]:
        """Return detailed information for a single door."""
        raise NotImplementedError("DoorManager.get_door not yet implemented")

    # ------------------------------------------------------------------
    # Mutation methods (stubs)
    # ------------------------------------------------------------------

    async def lock_door(self, door_id: str) -> Dict[str, Any]:
        """Lock a door. Returns preview data."""
        raise NotImplementedError("DoorManager.lock_door not yet implemented")

    async def unlock_door(self, door_id: str, duration: int | None = None) -> Dict[str, Any]:
        """Unlock a door. Returns preview data."""
        raise NotImplementedError("DoorManager.unlock_door not yet implemented")
