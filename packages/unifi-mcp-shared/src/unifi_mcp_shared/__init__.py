"""Shared MCP server patterns: permissions, confirmation, lazy loading, config."""

from unifi_mcp_shared.confirmation import (
    create_preview,
    preview_response,
    should_auto_confirm,
    toggle_preview,
    update_preview,
)
from unifi_mcp_shared.lazy_tools import (
    LazyToolLoader,
    build_tool_module_map,
    setup_lazy_loading,
)
from unifi_mcp_shared.meta_tools import register_load_tools, register_meta_tools
from unifi_mcp_shared.permissions import PermissionChecker

__all__ = [
    "LazyToolLoader",
    "PermissionChecker",
    "build_tool_module_map",
    "create_preview",
    "preview_response",
    "register_load_tools",
    "register_meta_tools",
    "setup_lazy_loading",
    "should_auto_confirm",
    "toggle_preview",
    "update_preview",
]
