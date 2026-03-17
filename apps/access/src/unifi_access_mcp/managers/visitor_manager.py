"""Visitor management for UniFi Access.

Provides methods to query and manage visitor passes
via the Access controller API.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from unifi_access_mcp.managers.connection_manager import AccessConnectionManager

logger = logging.getLogger(__name__)


class VisitorManager:
    """Reads and mutates visitor data from the Access controller."""

    def __init__(self, connection_manager: AccessConnectionManager) -> None:
        self._cm = connection_manager

    # ------------------------------------------------------------------
    # Read-only methods (stubs)
    # ------------------------------------------------------------------

    async def list_visitors(self) -> List[Dict[str, Any]]:
        """Return all visitors as summary dicts."""
        raise NotImplementedError("VisitorManager.list_visitors not yet implemented")

    async def get_visitor(self, visitor_id: str) -> Dict[str, Any]:
        """Return detailed information for a single visitor."""
        raise NotImplementedError("VisitorManager.get_visitor not yet implemented")

    # ------------------------------------------------------------------
    # Mutation methods (stubs)
    # ------------------------------------------------------------------

    async def create_visitor(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new visitor pass. Returns preview data."""
        raise NotImplementedError("VisitorManager.create_visitor not yet implemented")

    async def delete_visitor(self, visitor_id: str) -> Dict[str, Any]:
        """Delete a visitor pass. Returns preview data."""
        raise NotImplementedError("VisitorManager.delete_visitor not yet implemented")
