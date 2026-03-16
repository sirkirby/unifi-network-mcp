"""Shared MCP server patterns: permissions, confirmation, lazy loading, config."""

from unifi_mcp_shared.confirmation import (
    create_preview,
    preview_response,
    should_auto_confirm,
    toggle_preview,
    update_preview,
)
from unifi_mcp_shared.permissions import PermissionChecker

__all__ = [
    "PermissionChecker",
    "create_preview",
    "preview_response",
    "should_auto_confirm",
    "toggle_preview",
    "update_preview",
]
