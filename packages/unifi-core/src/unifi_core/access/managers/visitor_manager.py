"""Visitor management for UniFi Access.

Provides methods to query and manage visitor passes
via the Access controller API.

All methods use the proxy session path since visitor management is
not exposed by the py-unifi-access API client.

NOTE: Visitor endpoints were not directly visible in browser network
traces (visitors may be part of the user system under ulp-go).  The
paths below are best-effort guesses.  Each method includes graceful
error handling that returns an empty result with a clear message when
the endpoint returns 404.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from unifi_core.access.managers.connection_manager import AccessConnectionManager
from unifi_core.exceptions import UniFiConnectionError, UniFiNotFoundError

logger = logging.getLogger(__name__)


class VisitorManager:
    """Reads and mutates visitor data from the Access controller."""

    def __init__(self, connection_manager: AccessConnectionManager) -> None:
        self._cm = connection_manager

    # ------------------------------------------------------------------
    # Read-only methods
    # ------------------------------------------------------------------

    async def list_visitors(self) -> List[Dict[str, Any]]:
        """Return all visitors as summary dicts.

        Returns an empty list with a warning if the endpoint is not available
        (404), since the exact visitor API path has not been confirmed.
        """
        if not self._cm.has_proxy:
            raise UniFiConnectionError("No proxy session available for list_visitors")
        try:
            data = await self._cm.proxy_request("GET", "visitors")
            return self._cm.extract_data(data)
        except UniFiConnectionError as e:
            if "HTTP 404" in str(e):
                logger.warning(
                    "[visitors] Visitor endpoint returned 404 — endpoint path may not be correct. Returning empty list."
                )
                return []
            raise
        except Exception as e:
            logger.error("Failed to list visitors: %s", e, exc_info=True)
            raise

    async def get_visitor(self, visitor_id: str) -> Dict[str, Any]:
        """Return detailed information for a single visitor.

        Returns an error if the endpoint is not available (404).
        """
        if not visitor_id:
            raise ValueError("visitor_id is required")
        if not self._cm.has_proxy:
            raise UniFiConnectionError("No proxy session available for get_visitor")
        try:
            data = await self._cm.proxy_request("GET", f"visitors/{visitor_id}")
            return self._cm.extract_data(data)
        except UniFiConnectionError as e:
            if "HTTP 404" in str(e):
                logger.warning(
                    "[visitors] Visitor endpoint returned 404 for %s — endpoint path may not be correct.",
                    visitor_id,
                )
                raise UniFiNotFoundError(
                    "visitor",
                    visitor_id,
                    f"Visitor not found or endpoint not available: {visitor_id}. "
                    "The visitor API path has not been confirmed via browser inspection.",
                ) from e
            raise
        except Exception as e:
            logger.error("Failed to get visitor %s: %s", visitor_id, e, exc_info=True)
            raise

    # ------------------------------------------------------------------
    # Mutation methods (preview/confirm pattern)
    # ------------------------------------------------------------------

    async def create_visitor(
        self,
        name: str,
        access_start: str,
        access_end: str,
        **extra: Any,
    ) -> Dict[str, Any]:
        """Preview a visitor creation. Returns preview data for confirmation.

        Parameters
        ----------
        name:
            Visitor display name.
        access_start:
            ISO 8601 start time for the visitor pass.
        access_end:
            ISO 8601 end time for the visitor pass.
        **extra:
            Additional fields (e.g., email, phone, doors).
        """
        if not name:
            raise ValueError("name is required")
        if not access_start or not access_end:
            raise ValueError("access_start and access_end are required")

        visitor_data = {
            "name": name,
            "access_start": access_start,
            "access_end": access_end,
            **extra,
        }
        return {
            "visitor_data": visitor_data,
            "proposed_changes": {
                "action": "create",
                **visitor_data,
            },
        }

    async def apply_create_visitor(
        self,
        name: str,
        access_start: str,
        access_end: str,
        **extra: Any,
    ) -> Dict[str, Any]:
        """Execute the visitor creation on the controller."""
        if not self._cm.has_proxy:
            raise UniFiConnectionError("No proxy session available for create_visitor")
        try:
            payload = {
                "name": name,
                "access_start": access_start,
                "access_end": access_end,
                **extra,
            }
            result = await self._cm.proxy_request("POST", "visitors", json=payload)
            return {
                "action": "create",
                "result": "success",
                "data": self._cm.extract_data(result),
            }
        except UniFiConnectionError:
            raise
        except Exception as e:
            logger.error("Failed to create visitor: %s", e, exc_info=True)
            raise

    async def delete_visitor(self, visitor_id: str) -> Dict[str, Any]:
        """Preview a visitor deletion. Returns preview data for confirmation."""
        if not visitor_id:
            raise ValueError("visitor_id is required")

        current = await self.get_visitor(visitor_id)
        return {
            "visitor_id": visitor_id,
            "visitor_name": current.get("name"),
            "current_state": current,
            "proposed_changes": {
                "action": "delete",
            },
        }

    async def apply_delete_visitor(self, visitor_id: str) -> Dict[str, Any]:
        """Execute the visitor deletion on the controller."""
        if not self._cm.has_proxy:
            raise UniFiConnectionError("No proxy session available for delete_visitor")
        try:
            await self._cm.proxy_request("DELETE", f"visitors/{visitor_id}")
            return {
                "visitor_id": visitor_id,
                "action": "delete",
                "result": "success",
            }
        except UniFiConnectionError:
            raise
        except Exception as e:
            logger.error("Failed to delete visitor %s: %s", visitor_id, e, exc_info=True)
            raise
