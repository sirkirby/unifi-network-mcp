"""Credential management for UniFi Access.

Provides methods to query and manage access credentials (NFC cards, PINs,
mobile credentials) via the Access controller API.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from unifi_access_mcp.managers.connection_manager import AccessConnectionManager

logger = logging.getLogger(__name__)


class CredentialManager:
    """Reads and mutates credential data from the Access controller."""

    def __init__(self, connection_manager: AccessConnectionManager) -> None:
        self._cm = connection_manager

    # ------------------------------------------------------------------
    # Read-only methods (stubs)
    # ------------------------------------------------------------------

    async def list_credentials(self) -> List[Dict[str, Any]]:
        """Return all credentials as summary dicts."""
        raise NotImplementedError("CredentialManager.list_credentials not yet implemented")

    async def get_credential(self, credential_id: str) -> Dict[str, Any]:
        """Return detailed information for a single credential."""
        raise NotImplementedError("CredentialManager.get_credential not yet implemented")

    # ------------------------------------------------------------------
    # Mutation methods (stubs)
    # ------------------------------------------------------------------

    async def create_credential(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new credential. Returns preview data."""
        raise NotImplementedError("CredentialManager.create_credential not yet implemented")

    async def delete_credential(self, credential_id: str) -> Dict[str, Any]:
        """Delete a credential. Returns preview data."""
        raise NotImplementedError("CredentialManager.delete_credential not yet implemented")
