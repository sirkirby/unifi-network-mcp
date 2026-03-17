"""Credential tools for UniFi Access MCP server.

Provides tools for listing, inspecting, and managing access credentials
(NFC cards, PINs, mobile credentials).
"""

import logging
from typing import Any, Dict

from mcp.types import ToolAnnotations

from unifi_access_mcp.runtime import credential_manager, server

logger = logging.getLogger(__name__)


@server.tool(
    name="access_list_credentials",
    description=(
        "Lists all access credentials (NFC cards, PINs, mobile credentials) "
        "with their type, status, and assigned user."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def access_list_credentials() -> Dict[str, Any]:
    """List all credentials."""
    logger.info("access_list_credentials tool called")
    try:
        credentials = await credential_manager.list_credentials()
        return {"success": True, "data": {"credentials": credentials, "count": len(credentials)}}
    except NotImplementedError:
        return {"success": False, "error": "Credential listing not yet implemented"}
    except Exception as e:
        logger.error("Error listing credentials: %s", e, exc_info=True)
        return {"success": False, "error": f"Failed to list credentials: {e}"}


@server.tool(
    name="access_get_credential",
    description="Returns detailed information for a single access credential.",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def access_get_credential(credential_id: str) -> Dict[str, Any]:
    """Get detailed credential information by ID."""
    logger.info("access_get_credential tool called for %s", credential_id)
    try:
        detail = await credential_manager.get_credential(credential_id)
        return {"success": True, "data": detail}
    except NotImplementedError:
        return {"success": False, "error": "Credential detail not yet implemented"}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error("Error getting credential %s: %s", credential_id, e, exc_info=True)
        return {"success": False, "error": f"Failed to get credential: {e}"}


logger.info("Credential tools registered: access_list_credentials, access_get_credential")
