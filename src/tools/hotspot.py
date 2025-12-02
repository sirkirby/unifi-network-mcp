"""
UniFi Network MCP hotspot voucher tools.

This module provides MCP tools to manage hotspot vouchers on a UniFi Network Controller.
"""

import logging
from typing import Any, Dict, Optional

from src.runtime import config, server
from src.utils.confirmation import create_preview, preview_response, should_auto_confirm
from src.utils.permissions import parse_permission

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependencies
_hotspot_manager = None


def _get_hotspot_manager():
    """Lazy-load the hotspot manager to avoid circular imports."""
    global _hotspot_manager
    if _hotspot_manager is None:
        from src.managers.hotspot_manager import HotspotManager
        from src.runtime import get_connection_manager

        _hotspot_manager = HotspotManager(get_connection_manager())
    return _hotspot_manager


@server.tool(
    name="unifi_list_vouchers",
    description="""List all hotspot vouchers for the current site.

Returns voucher codes, expiration times, usage quotas, and bandwidth limits.
Vouchers are used for guest network access in captive portal setups.""",
)
async def list_vouchers() -> Dict[str, Any]:
    """List all hotspot vouchers."""
    try:
        hotspot_manager = _get_hotspot_manager()
        vouchers = await hotspot_manager.get_vouchers()

        # Format vouchers for readability
        formatted_vouchers = []
        for v in vouchers:
            formatted = {
                "_id": v.get("_id"),
                "code": v.get("code"),
                "quota": v.get("quota", 1),
                "duration_minutes": v.get("duration"),
                "used": v.get("used", 0),
                "create_time": v.get("create_time"),
                "note": v.get("note"),
            }
            # Add bandwidth limits if set
            if v.get("qos_rate_max_up"):
                formatted["up_limit_kbps"] = v.get("qos_rate_max_up")
            if v.get("qos_rate_max_down"):
                formatted["down_limit_kbps"] = v.get("qos_rate_max_down")
            if v.get("qos_usage_quota"):
                formatted["data_limit_mb"] = v.get("qos_usage_quota")
            formatted_vouchers.append(formatted)

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
    description="Get detailed information about a specific voucher by its ID",
)
async def get_voucher_details(voucher_id: str) -> Dict[str, Any]:
    """Get details for a specific voucher."""
    try:
        hotspot_manager = _get_hotspot_manager()
        voucher = await hotspot_manager.get_voucher_details(voucher_id)

        if voucher:
            return {
                "success": True,
                "site": hotspot_manager._connection.site,
                "voucher": voucher,
            }
        return {
            "success": False,
            "error": f"Voucher not found with ID: {voucher_id}",
        }
    except Exception as e:
        logger.error(f"Error getting voucher details for {voucher_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_create_voucher",
    description="""Create hotspot voucher(s) for guest network access.

Vouchers can have:
- Time limits: How long the voucher is valid after activation
- Usage quota: Single-use (1), multi-use (0), or n-times usable
- Bandwidth limits: Upload/download speed caps in Kbps
- Data caps: Total data transfer limit in MB""",
    permission_category="vouchers",
    permission_action="create",
)
async def create_voucher(
    expire_minutes: int = 1440,
    count: int = 1,
    quota: int = 1,
    note: Optional[str] = None,
    up_limit_kbps: Optional[int] = None,
    down_limit_kbps: Optional[int] = None,
    bytes_limit_mb: Optional[int] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Create one or more hotspot vouchers."""
    if not parse_permission(config.permissions, "voucher", "create"):
        logger.warning("Permission denied for creating vouchers.")
        return {"success": False, "error": "Permission denied to create vouchers."}

    if expire_minutes < 1:
        return {"success": False, "error": "expire_minutes must be at least 1."}

    if count < 1 or count > 10000:
        return {"success": False, "error": "count must be between 1 and 10000."}

    if not confirm and not should_auto_confirm():
        resource_data = {
            "count": count,
            "expire_minutes": expire_minutes,
            "quota": quota,
        }
        if note:
            resource_data["note"] = note
        if up_limit_kbps:
            resource_data["up_limit_kbps"] = up_limit_kbps
        if down_limit_kbps:
            resource_data["down_limit_kbps"] = down_limit_kbps
        if bytes_limit_mb:
            resource_data["bytes_limit_mb"] = bytes_limit_mb

        return create_preview(
            resource_type="voucher",
            resource_data=resource_data,
            resource_name=f"{count} voucher(s)",
        )

    try:
        hotspot_manager = _get_hotspot_manager()
        vouchers = await hotspot_manager.create_voucher(
            expire_minutes=expire_minutes,
            count=count,
            quota=quota,
            note=note,
            up_limit_kbps=up_limit_kbps,
            down_limit_kbps=down_limit_kbps,
            bytes_limit_mb=bytes_limit_mb,
        )

        if vouchers:
            return {
                "success": True,
                "message": f"Created {len(vouchers)} voucher(s).",
                "site": hotspot_manager._connection.site,
                "count": len(vouchers),
                "vouchers": vouchers,
            }
        return {"success": False, "error": "Failed to create vouchers."}
    except Exception as e:
        logger.error(f"Error creating vouchers: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_revoke_voucher",
    description="Revoke/delete a hotspot voucher by its ID, preventing further use",
    permission_category="vouchers",
    permission_action="update",
)
async def revoke_voucher(voucher_id: str, confirm: bool = False) -> Dict[str, Any]:
    """Revoke a hotspot voucher."""
    if not parse_permission(config.permissions, "voucher", "update"):
        logger.warning(f"Permission denied for revoking voucher ({voucher_id}).")
        return {"success": False, "error": "Permission denied to revoke vouchers."}

    try:
        hotspot_manager = _get_hotspot_manager()

        # Fetch voucher details first for preview
        if not confirm and not should_auto_confirm():
            voucher = await hotspot_manager.get_voucher_details(voucher_id)
            if not voucher:
                return {"success": False, "error": f"Voucher not found with ID: {voucher_id}"}

            current_state = {}
            if voucher.get("code"):
                current_state["code"] = voucher.get("code")
            if voucher.get("note"):
                current_state["note"] = voucher.get("note")
            if voucher.get("quota"):
                current_state["quota"] = voucher.get("quota")
            if voucher.get("used") is not None:
                current_state["used"] = voucher.get("used")

            return preview_response(
                action="revoke",
                resource_type="voucher",
                resource_id=voucher_id,
                resource_name=voucher.get("code"),
                current_state=current_state,
                proposed_changes={"status": "revoked"},
                warnings=["This voucher will no longer be usable"],
            )

        success = await hotspot_manager.revoke_voucher(voucher_id)

        if success:
            return {
                "success": True,
                "message": f"Voucher {voucher_id} revoked successfully.",
            }
        return {"success": False, "error": f"Failed to revoke voucher {voucher_id}."}
    except Exception as e:
        logger.error(f"Error revoking voucher {voucher_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
