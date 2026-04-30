"""Liveview management for UniFi Protect.

Provides methods to list, create, and delete liveview configurations
via the uiprotect bootstrap data.

Liveviews are multi-camera layout configurations used by the Protect app
and UniFi Viewport devices.  Each liveview has:
- A name and layout grid size
- A list of slots, each containing camera IDs and cycle settings
- An owner (user who created it)
- Global/default flags

Key API surface:
- ``client.bootstrap.liveviews`` -- dict of Liveview objects
- ``client.get_liveviews()`` -- fetch from NVR directly
- ``Liveview.save_device(data_before)`` -- save changes
- No dedicated create/delete API in uiprotect; use save_device pattern
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from unifi_core.exceptions import UniFiNotFoundError
from unifi_core.protect.managers.connection_manager import ProtectConnectionManager

logger = logging.getLogger(__name__)


class LiveviewManager:
    """Domain logic for UniFi Protect liveviews."""

    def __init__(self, connection_manager: ProtectConnectionManager) -> None:
        self._cm = connection_manager

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_liveview(self, liveview_id: str):
        """Retrieve a Liveview object by ID, raising UniFiNotFoundError if not found."""
        liveviews = self._cm.client.bootstrap.liveviews
        liveview = liveviews.get(liveview_id)
        if liveview is None:
            raise UniFiNotFoundError("liveview", liveview_id)
        return liveview

    @staticmethod
    def _format_liveview_summary(liveview) -> Dict[str, Any]:
        """Format a liveview into a summary dict with essential fields."""
        slots: List[Dict[str, Any]] = []
        for slot in liveview.slots or []:
            slots.append(
                {
                    "camera_ids": list(slot.camera_ids) if slot.camera_ids else [],
                    "cycle_mode": slot.cycle_mode,
                    "cycle_interval": slot.cycle_interval,
                }
            )

        return {
            "id": liveview.id,
            "name": liveview.name,
            "is_default": liveview.is_default,
            "is_global": liveview.is_global,
            "layout": liveview.layout,
            "owner_id": liveview.owner_id,
            "slots": slots,
            "slot_count": len(slots),
            "camera_count": sum(len(s.get("camera_ids", [])) for s in slots),
        }

    # ------------------------------------------------------------------
    # Read-only methods
    # ------------------------------------------------------------------

    async def list_liveviews(self) -> List[Dict[str, Any]]:
        """Return all liveviews as summary dicts."""
        liveviews = self._cm.client.bootstrap.liveviews
        return [self._format_liveview_summary(lv) for lv in liveviews.values()]

    # ------------------------------------------------------------------
    # Mutation methods (preview / apply)
    # ------------------------------------------------------------------

    async def create_liveview(self, name: str, camera_ids: List[str]) -> Dict[str, Any]:
        """Return preview data for creating a new liveview.

        Note: uiprotect does not expose a public create_liveview API method.
        Liveview creation requires either the internal REST API or the
        save_device pattern which is not well-suited for new object creation.

        This method validates the input and returns a preview of what would
        be created.
        """
        # Validate camera IDs exist
        cameras = self._cm.client.bootstrap.cameras
        valid_ids: List[str] = []
        invalid_ids: List[str] = []
        for cid in camera_ids:
            if cid in cameras:
                valid_ids.append(cid)
            else:
                invalid_ids.append(cid)

        return {
            "name": name,
            "camera_ids": valid_ids,
            "invalid_camera_ids": invalid_ids,
            "camera_count": len(valid_ids),
            "supported": False,
            "message": (
                "Liveview creation is not directly supported by the uiprotect Python API. "
                "Liveviews are typically created through the Protect web UI or the UniFi OS "
                "REST API. The camera IDs have been validated and are listed above."
            ),
        }

    async def delete_liveview(self, liveview_id: str) -> Dict[str, Any]:
        """Return preview data for deleting a liveview.

        Note: uiprotect does not expose a public delete_liveview API method.
        This returns information about the liveview and the limitation.
        """
        liveview = self._get_liveview(liveview_id)

        return {
            "liveview_id": liveview_id,
            "liveview_name": liveview.name,
            "is_default": liveview.is_default,
            "is_global": liveview.is_global,
            "slot_count": len(liveview.slots) if liveview.slots else 0,
            "supported": False,
            "message": (
                "Liveview deletion is not directly supported by the uiprotect Python API. "
                "Liveviews can be deleted through the Protect web UI or the UniFi OS REST API."
            ),
        }
