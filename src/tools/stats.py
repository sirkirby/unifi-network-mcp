"""
Unifi Network MCP statistics tools.

This module provides MCP tools to fetch statistics from a Unifi Network Controller.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from src.runtime import server, config, stats_manager, client_manager, system_manager
import mcp.types as types # Import the types module
from src.utils.permissions import parse_permission

logger = logging.getLogger(__name__)

@server.tool(
    name="unifi_get_network_stats",
    description="Get network statistics from the Unifi Network controller"
)
async def get_network_stats(duration: str = "hourly") -> Dict[str, Any]:
    """Implementation for getting network stats."""
    try:
        duration_hours = {"hourly": 1, "daily": 24, "weekly": 168, "monthly": 720}.get(duration, 1)
        stats = await stats_manager.get_network_stats(duration_hours=duration_hours)
        summary = {
            "total_rx_bytes": sum(e.get("rx_bytes", 0) for e in stats),
            "total_tx_bytes": sum(e.get("tx_bytes", 0) for e in stats),
            "total_bytes": sum((e.get("rx_bytes", 0) + e.get("tx_bytes", 0)) for e in stats),
            "avg_clients": int(sum(e.get("num_user", 0) or e.get("num_active_user", 0) for e in stats) / max(1, len(stats))) if stats else 0
        }
        return {"success": True, "site": stats_manager._connection.site, "duration": duration, "summary": summary, "stats": stats}
    except Exception as e:
        logger.error(f"Error getting network stats: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_get_client_stats",
    description="Get statistics for a specific client/device"
)
async def get_client_stats(client_id: str, duration: str = "hourly") -> Dict[str, Any]:
    """Implementation for getting client stats."""
    try:
        duration_hours = {"hourly": 1, "daily": 24, "weekly": 168, "monthly": 720}.get(duration, 1)
        client_details = await client_manager.get_client_details(client_id)
        if not client_details:
            return {"success": False, "error": f"Client '{client_id}' not found"}
        
        client_name = client_details.get("name") or client_details.get("hostname") or client_details.get("mac", "Unknown")
        actual_client_id = client_details.get("_id", client_id)
        
        stats = await stats_manager.get_client_stats(actual_client_id, duration_hours=duration_hours)
        summary = {
            "total_rx_bytes": sum(e.get("rx_bytes", 0) for e in stats),
            "total_tx_bytes": sum(e.get("tx_bytes", 0) for e in stats),
            "total_bytes": sum((e.get("rx_bytes", 0) + e.get("tx_bytes", 0)) for e in stats),
        }
        return {"success": True, "site": stats_manager._connection.site, "client_id": client_id, "client_name": client_name, "duration": duration, "summary": summary, "stats": stats}
    except Exception as e:
        logger.error(f"Error getting client stats for {client_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_get_device_stats",
    description="Get statistics for a specific device (access point, switch, etc.)"
)
async def get_device_stats(device_id: str, duration: str = "hourly") -> Dict[str, Any]:
    """Implementation for getting device stats."""
    try:
        duration_hours = {"hourly": 1, "daily": 24, "weekly": 168, "monthly": 720}.get(duration, 1)
        device_details = await system_manager.get_device_details(device_id)
        if not device_details:
            return {"success": False, "error": f"Device '{device_id}' not found"}
        
        device_name = device_details.get("name") or device_details.get("model", "Unknown")
        actual_device_id = device_details.get("_id", device_id)
        device_type = device_details.get("type", "unknown")

        stats = await stats_manager.get_device_stats(actual_device_id, duration_hours=duration_hours)
        summary = {
            "total_rx_bytes": sum(e.get("rx_bytes", 0) for e in stats),
            "total_tx_bytes": sum(e.get("tx_bytes", 0) for e in stats),
            "total_bytes": sum((e.get("rx_bytes", 0) + e.get("tx_bytes", 0)) for e in stats),
        }
        if device_type == "uap" and stats:
            summary["avg_clients"] = int(sum(e.get("num_sta", 0) for e in stats) / max(1, len(stats)))
            summary["max_clients"] = max(e.get("num_sta", 0) for e in stats)
        
        return {"success": True, "site": stats_manager._connection.site, "device_id": device_id, "device_name": device_name, "device_type": device_type, "duration": duration, "summary": summary, "stats": stats}
    except Exception as e:
        logger.error(f"Error getting device stats for {device_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_get_top_clients",
    description="Get a list of top clients by usage (sorted by total bytes)"
)
async def get_top_clients(duration: str = "daily", limit: int = 10) -> Dict[str, Any]:
    """Implementation for getting top clients by usage."""
    try:
        duration_hours = {"hourly": 1, "daily": 24, "weekly": 168, "monthly": 720}.get(duration, 1)
        top_client_stats = await stats_manager.get_top_clients(duration_hours=duration_hours, limit=limit)
        
        enhanced_clients = []
        for entry in top_client_stats:
            mac = entry.get("mac")
            name = "Unknown"
            if mac:
                details = await client_manager.get_client_details(mac)
                if details and hasattr(details, 'raw'):
                    name = details.raw.get("name") or details.raw.get("hostname") or mac
                elif details:
                     name = mac
            entry["name"] = name
            enhanced_clients.append(entry)
            
        return {"success": True, "site": stats_manager._connection.site, "duration": duration, "limit": limit, "top_clients": enhanced_clients}
    except Exception as e:
        logger.error(f"Error getting top clients: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_get_dpi_stats",
    description="Get Deep Packet Inspection (DPI) statistics (applications and categories)"
)
async def get_dpi_stats() -> Dict[str, Any]:
    """Implementation for getting DPI stats."""
    try:
        dpi_stats_result = await stats_manager.get_dpi_stats()
        
        def serialize_dpi(item):
            return item.raw if hasattr(item, 'raw') else item

        serialized_apps = [serialize_dpi(app) for app in dpi_stats_result.get("applications", [])]
        serialized_cats = [serialize_dpi(cat) for cat in dpi_stats_result.get("categories", [])]
        
        return {
            "success": True, 
            "site": stats_manager._connection.site, 
            "dpi_stats": {
                "applications": serialized_apps,
                "categories": serialized_cats
            }
        }
    except Exception as e:
        logger.error(f"Error getting DPI stats: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@server.tool(
    name="unifi_get_alerts",
    description="Get recent alerts from the Unifi Network controller"
)
async def get_alerts(limit: int = 10, include_archived: bool = False) -> Dict[str, Any]:
    """Implementation for getting alerts."""
    try:
        alerts = await stats_manager.get_alerts(limit=limit, include_archived=include_archived)
        return {"success": True, "site": stats_manager._connection.site, "limit": limit, "include_archived": include_archived, "alerts": alerts}
    except Exception as e:
        logger.error(f"Error getting alerts: {e}", exc_info=True)
        return {"success": False, "error": str(e)} 