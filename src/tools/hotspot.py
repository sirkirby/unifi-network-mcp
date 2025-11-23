"""Hotspot tools for UniFi Network MCP server.

Provides MCP tools for managing hotspot vouchers including listing,
creating, and revoking vouchers for guest network access.
"""

import logging
import json
from typing import Dict, Any, Optional

from src.runtime import server, config
from src.utils.permissions import parse_permission

logger = logging.getLogger(__name__)


def _get_hotspot_manager():
    """Lazy import to avoid circular dependency."""
    from src.runtime import hotspot_manager
    return hotspot_manager


@server.tool(
    name="unifi_list_vouchers",
    description="List all hotspot vouchers on the UniFi controller for the current site.",
)
async def list_vouchers() -> Dict[str, Any]:
    """Lists all hotspot vouchers configured for the current UniFi site.

    Returns:
        A dictionary containing:
        - success (bool): Indicates if the operation was successful.
        - site (str): The identifier of the UniFi site queried.
        - count (int): The number of vouchers found.
        - vouchers (List[Dict]): A list of vouchers with summary info:
            - id (str): The unique identifier (_id) of the voucher.
            - code (str): The voucher code (for guest login).
            - quota (int): Usage quota (0=multi-use, 1=single-use).
            - duration (int): Validity duration in minutes.
            - used (int): Number of times the voucher has been used.
            - status (str): Status description.
            - note (str): Optional note attached to the voucher.
            - create_time (int): Unix timestamp of creation.
        - error (str, optional): An error message if the operation failed.

    Example response (success):
    {
        "success": True,
        "site": "default",
        "count": 2,
        "vouchers": [
            {
                "id": "60d4e5f6a7b8c9d0e1f2a3b4",
                "code": "12345-67890",
                "quota": 1,
                "duration": 1440,
                "used": 0,
                "status": "unused",
                "note": "Guest WiFi",
                "create_time": 1700000000
            }
        ]
    }
    """
    if not parse_permission(config.permissions, "voucher", "read"):
        logger.warning("Permission denied for listing vouchers.")
        return {"success": False, "error": "Permission denied to list vouchers."}

    try:
        hotspot_manager = _get_hotspot_manager()
        vouchers = await hotspot_manager.get_vouchers()

        formatted_vouchers = []
        for v in vouchers:
            used = v.get("used", 0)
            quota = v.get("quota", 1)

            # Determine status
            if quota == 0:
                status = "multi-use"
            elif used >= quota:
                status = "exhausted"
            else:
                status = "unused" if used == 0 else f"used {used}/{quota}"

            formatted_vouchers.append({
                "id": v.get("_id"),
                "code": v.get("code"),
                "quota": quota,
                "duration": v.get("duration"),
                "used": used,
                "status": status,
                "note": v.get("note", ""),
                "create_time": v.get("create_time"),
                "qos_overwrite": v.get("qos_overwrite", False),
                "up_limit": v.get("qos_rate_max_up"),
                "down_limit": v.get("qos_rate_max_down"),
                "bytes_limit": v.get("qos_usage_quota"),
            })

        return {
            "success": True,
            "site": hotspot_manager._connection.site,
            "count": len(formatted_vouchers),
            "vouchers": formatted_vouchers,
        }
    except Exception as e:
        logger.error(f"Error listing vouchers: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_get_voucher_details",
    description="Get details for a specific hotspot voucher by ID.",
)
async def get_voucher_details(voucher_id: str) -> Dict[str, Any]:
    """Gets the detailed information of a specific voucher by its ID.

    Args:
        voucher_id (str): The unique identifier (_id) of the voucher.

    Returns:
        A dictionary containing:
        - success (bool): Indicates if the operation was successful.
        - site (str): The identifier of the UniFi site queried.
        - voucher_id (str): The ID of the voucher requested.
        - details (Dict[str, Any]): Full voucher details from the controller.
        - error (str, optional): An error message if the operation failed.
    """
    if not parse_permission(config.permissions, "voucher", "read"):
        logger.warning(f"Permission denied for getting voucher details ({voucher_id}).")
        return {"success": False, "error": "Permission denied to get voucher details."}

    try:
        if not voucher_id:
            return {"success": False, "error": "voucher_id is required"}

        hotspot_manager = _get_hotspot_manager()
        voucher = await hotspot_manager.get_voucher_details(voucher_id)

        if voucher:
            return {
                "success": True,
                "site": hotspot_manager._connection.site,
                "voucher_id": voucher_id,
                "details": json.loads(json.dumps(voucher, default=str)),
            }
        else:
            return {
                "success": False,
                "error": f"Voucher with ID '{voucher_id}' not found.",
            }
    except Exception as e:
        logger.error(f"Error getting voucher {voucher_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_create_voucher",
    description=(
        "Create one or more hotspot vouchers for guest network access. "
        "Requires confirmation."
    ),
    permission_category="vouchers",
    permission_action="create",
)
async def create_voucher(
    expire_minutes: int,
    count: int = 1,
    quota: int = 1,
    note: Optional[str] = None,
    up_limit_kbps: Optional[int] = None,
    down_limit_kbps: Optional[int] = None,
    bytes_limit_mb: Optional[int] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Creates one or more hotspot vouchers for guest WiFi access.

    Args:
        expire_minutes (int): Minutes the voucher is valid after first use.
            Common values: 60 (1 hour), 480 (8 hours), 1440 (24 hours),
            10080 (1 week), 43200 (30 days).
        count (int): Number of vouchers to create (default 1, max typically 10000).
        quota (int): Usage quota per voucher:
            - 0 = unlimited/multi-use (any number of devices)
            - 1 = single-use (one device only, default)
            - n = can be used by n devices
        note (str, optional): Note for the voucher (shown when printing).
        up_limit_kbps (int, optional): Upload speed limit in Kbps.
        down_limit_kbps (int, optional): Download speed limit in Kbps.
        bytes_limit_mb (int, optional): Data transfer limit in MB.
        confirm (bool): Must be True to execute. Defaults to False.

    Returns:
        A dictionary containing:
        - success (bool): Whether the operation succeeded.
        - site (str): The UniFi site.
        - created_count (int): Number of vouchers created.
        - vouchers (List[Dict]): List of created vouchers with codes.
        - error (str, optional): Error message if failed.

    Example:
        Create 5 single-use vouchers valid for 24 hours:
        {
            "expire_minutes": 1440,
            "count": 5,
            "quota": 1,
            "note": "Conference guests",
            "confirm": true
        }
    """
    if not parse_permission(config.permissions, "voucher", "create"):
        logger.warning("Permission denied for creating vouchers.")
        return {"success": False, "error": "Permission denied to create vouchers."}

    if not confirm:
        return {
            "success": False,
            "error": "Confirmation required. Set 'confirm' to true.",
            "preview": {
                "expire_minutes": expire_minutes,
                "count": count,
                "quota": quota,
                "note": note,
                "up_limit_kbps": up_limit_kbps,
                "down_limit_kbps": down_limit_kbps,
                "bytes_limit_mb": bytes_limit_mb,
            },
        }

    # Validation
    if expire_minutes <= 0:
        return {"success": False, "error": "expire_minutes must be greater than 0"}
    if count <= 0:
        return {"success": False, "error": "count must be greater than 0"}
    if quota < 0:
        return {"success": False, "error": "quota cannot be negative"}

    try:
        hotspot_manager = _get_hotspot_manager()
        logger.info(
            f"Creating {count} voucher(s): {expire_minutes}min, quota={quota}"
        )

        created_vouchers = await hotspot_manager.create_voucher(
            expire_minutes=expire_minutes,
            count=count,
            quota=quota,
            note=note,
            up_limit_kbps=up_limit_kbps,
            down_limit_kbps=down_limit_kbps,
            bytes_limit_mb=bytes_limit_mb,
        )

        if created_vouchers:
            # Format the response
            voucher_codes = [
                {
                    "id": v.get("_id"),
                    "code": v.get("code"),
                    "duration": v.get("duration"),
                    "quota": v.get("quota"),
                }
                for v in created_vouchers
            ]

            return {
                "success": True,
                "site": hotspot_manager._connection.site,
                "message": f"Successfully created {len(created_vouchers)} voucher(s).",
                "created_count": len(created_vouchers),
                "vouchers": voucher_codes,
            }
        else:
            return {
                "success": False,
                "error": "Failed to create vouchers. Check server logs.",
            }

    except Exception as e:
        logger.error(f"Error creating vouchers: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_revoke_voucher",
    description="Revoke/delete a hotspot voucher by ID. Requires confirmation.",
    permission_category="vouchers",
    permission_action="update",
)
async def revoke_voucher(
    voucher_id: str,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Revokes (deletes) a hotspot voucher, making it unusable.

    Args:
        voucher_id (str): The unique identifier (_id) of the voucher to revoke.
        confirm (bool): Must be True to execute. Defaults to False.

    Returns:
        A dictionary containing:
        - success (bool): Whether the operation succeeded.
        - voucher_id (str): The ID of the revoked voucher.
        - message (str): Confirmation message.
        - error (str, optional): Error message if failed.
    """
    if not parse_permission(config.permissions, "voucher", "update"):
        logger.warning(f"Permission denied for revoking voucher ({voucher_id}).")
        return {"success": False, "error": "Permission denied to revoke vouchers."}

    if not voucher_id:
        return {"success": False, "error": "voucher_id is required"}

    if not confirm:
        # Fetch voucher details for preview
        hotspot_manager = _get_hotspot_manager()
        voucher = await hotspot_manager.get_voucher_details(voucher_id)
        if voucher:
            return {
                "success": False,
                "error": "Confirmation required. Set 'confirm' to true.",
                "preview": {
                    "voucher_id": voucher_id,
                    "code": voucher.get("code"),
                    "note": voucher.get("note"),
                    "action": "revoke (delete)",
                },
            }
        else:
            return {
                "success": False,
                "error": f"Voucher with ID '{voucher_id}' not found.",
            }

    try:
        hotspot_manager = _get_hotspot_manager()

        # Verify voucher exists before attempting to revoke
        voucher = await hotspot_manager.get_voucher_details(voucher_id)
        if not voucher:
            return {
                "success": False,
                "error": f"Voucher with ID '{voucher_id}' not found.",
            }

        voucher_code = voucher.get("code", "unknown")

        success = await hotspot_manager.revoke_voucher(voucher_id)

        if success:
            logger.info(f"Successfully revoked voucher {voucher_id} (code: {voucher_code})")
            return {
                "success": True,
                "voucher_id": voucher_id,
                "message": f"Voucher '{voucher_code}' has been revoked.",
            }
        else:
            return {
                "success": False,
                "error": f"Failed to revoke voucher {voucher_id}. Check server logs.",
            }

    except Exception as e:
        logger.error(f"Error revoking voucher {voucher_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
