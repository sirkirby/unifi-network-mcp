"""Door management for UniFi Access.

Provides methods to query door state, lock/unlock doors, and manage
door configurations via the Access controller API.

Dual-path routing: tries the API client (py-unifi-access) first when
available, then falls back to the proxy session path.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from unifi_access_mcp.managers.connection_manager import AccessConnectionManager
from unifi_core.exceptions import UniFiConnectionError

logger = logging.getLogger(__name__)


class DoorManager:
    """Reads and mutates door data from the Access controller."""

    def __init__(self, connection_manager: AccessConnectionManager) -> None:
        self._cm = connection_manager

    # ------------------------------------------------------------------
    # Read-only methods
    # ------------------------------------------------------------------

    async def list_doors(self) -> List[Dict[str, Any]]:
        """Return all doors as summary dicts.

        Tries the API client first, then falls back to the proxy path.
        """
        try:
            if self._cm.has_api_client:
                doors = await self._cm.api_client.get_doors()
                return [
                    {
                        "id": d.id,
                        "name": d.name,
                        "door_position_status": getattr(d, "door_position_status", None),
                        "lock_relay_status": getattr(d, "lock_relay_status", None),
                    }
                    for d in doors
                ]
            elif self._cm.has_proxy:
                data = await self._cm.proxy_request("GET", "doors")
                return data.get("data", data) if isinstance(data, dict) else data
            else:
                raise UniFiConnectionError("No auth path available for list_doors")
        except UniFiConnectionError:
            raise
        except Exception as e:
            logger.error("Failed to list doors: %s", e, exc_info=True)
            raise

    async def get_door(self, door_id: str) -> Dict[str, Any]:
        """Return detailed information for a single door.

        Tries the API client first, then falls back to the proxy path.
        """
        if not door_id:
            raise ValueError("door_id is required")
        try:
            if self._cm.has_api_client:
                door = await self._cm.api_client.get_door(door_id)
                return {
                    "id": door.id,
                    "name": door.name,
                    "door_position_status": getattr(door, "door_position_status", None),
                    "lock_relay_status": getattr(door, "lock_relay_status", None),
                    "camera_resource_id": getattr(door, "camera_resource_id", None),
                    "door_guard": getattr(door, "door_guard", None),
                }
            elif self._cm.has_proxy:
                data = await self._cm.proxy_request("GET", f"doors/{door_id}")
                return data.get("data", data) if isinstance(data, dict) else data
            else:
                raise UniFiConnectionError("No auth path available for get_door")
        except (UniFiConnectionError, ValueError):
            raise
        except Exception as e:
            logger.error("Failed to get door %s: %s", door_id, e, exc_info=True)
            raise

    async def get_door_status(self, door_id: str) -> Dict[str, Any]:
        """Return current lock/position status for a single door.

        Tries the API client first, then falls back to the proxy path.
        """
        if not door_id:
            raise ValueError("door_id is required")
        try:
            if self._cm.has_api_client:
                door = await self._cm.api_client.get_door(door_id)
                return {
                    "id": door.id,
                    "name": door.name,
                    "door_position_status": getattr(door, "door_position_status", None),
                    "lock_relay_status": getattr(door, "lock_relay_status", None),
                }
            elif self._cm.has_proxy:
                data = await self._cm.proxy_request("GET", f"doors/{door_id}")
                raw = data.get("data", data) if isinstance(data, dict) else data
                if isinstance(raw, dict):
                    return {
                        "id": raw.get("id", door_id),
                        "name": raw.get("name"),
                        "door_position_status": raw.get("door_position_status"),
                        "lock_relay_status": raw.get("lock_relay_status"),
                    }
                return raw
            else:
                raise UniFiConnectionError("No auth path available for get_door_status")
        except (UniFiConnectionError, ValueError):
            raise
        except Exception as e:
            logger.error("Failed to get door status %s: %s", door_id, e, exc_info=True)
            raise

    async def list_door_groups(self) -> List[Dict[str, Any]]:
        """Return all door groups.

        This is only available via the proxy path (private API).
        """
        try:
            if self._cm.has_proxy:
                data = await self._cm.proxy_request("GET", "door_groups")
                return data.get("data", data) if isinstance(data, dict) else data
            else:
                raise UniFiConnectionError("No auth path available for list_door_groups (proxy session required)")
        except UniFiConnectionError:
            raise
        except Exception as e:
            logger.error("Failed to list door groups: %s", e, exc_info=True)
            raise

    # ------------------------------------------------------------------
    # Mutation methods (preview/confirm pattern)
    # ------------------------------------------------------------------

    async def unlock_door(self, door_id: str, duration: int = 2) -> Dict[str, Any]:
        """Preview an unlock operation. Returns preview data for confirmation.

        Parameters
        ----------
        door_id:
            UUID of the door to unlock.
        duration:
            Unlock duration in seconds (default 2).
        """
        if not door_id:
            raise ValueError("door_id is required")
        if duration < 1:
            raise ValueError("duration must be at least 1 second")

        # Get current state for preview
        current = await self.get_door_status(door_id)
        return {
            "door_id": door_id,
            "door_name": current.get("name"),
            "current_state": {
                "lock_relay_status": current.get("lock_relay_status"),
                "door_position_status": current.get("door_position_status"),
            },
            "proposed_changes": {
                "action": "unlock",
                "duration_seconds": duration,
            },
        }

    async def apply_unlock_door(self, door_id: str, duration: int = 2) -> Dict[str, Any]:
        """Execute the unlock operation on the controller.

        Tries the API client first, then falls back to the proxy path.
        """
        try:
            if self._cm.has_api_client:
                await self._cm.api_client.unlock_door(door_id)
                return {
                    "door_id": door_id,
                    "action": "unlock",
                    "duration_seconds": duration,
                    "result": "success",
                }
            elif self._cm.has_proxy:
                await self._cm.proxy_request(
                    "PUT",
                    f"doors/{door_id}/unlock",
                    json={"duration": duration},
                )
                return {
                    "door_id": door_id,
                    "action": "unlock",
                    "duration_seconds": duration,
                    "result": "success",
                }
            else:
                raise UniFiConnectionError("No auth path available for unlock_door")
        except (UniFiConnectionError, ValueError):
            raise
        except Exception as e:
            logger.error("Failed to unlock door %s: %s", door_id, e, exc_info=True)
            raise

    async def lock_door(self, door_id: str) -> Dict[str, Any]:
        """Preview a lock operation. Returns preview data for confirmation.

        Lock is only available via the proxy path (private API).
        """
        if not door_id:
            raise ValueError("door_id is required")

        # Get current state for preview
        current = await self.get_door_status(door_id)
        return {
            "door_id": door_id,
            "door_name": current.get("name"),
            "current_state": {
                "lock_relay_status": current.get("lock_relay_status"),
                "door_position_status": current.get("door_position_status"),
            },
            "proposed_changes": {
                "action": "lock",
            },
        }

    async def apply_lock_door(self, door_id: str) -> Dict[str, Any]:
        """Execute the lock operation on the controller.

        Lock is only available via the proxy path (private API).
        """
        try:
            if self._cm.has_proxy:
                await self._cm.proxy_request("PUT", f"doors/{door_id}/lock")
                return {
                    "door_id": door_id,
                    "action": "lock",
                    "result": "success",
                }
            else:
                raise UniFiConnectionError("No auth path available for lock_door (proxy session required)")
        except (UniFiConnectionError, ValueError):
            raise
        except Exception as e:
            logger.error("Failed to lock door %s: %s", door_id, e, exc_info=True)
            raise
