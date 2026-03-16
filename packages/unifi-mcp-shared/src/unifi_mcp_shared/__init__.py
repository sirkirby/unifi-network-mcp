"""Shared MCP server patterns: permissions, confirmation, lazy loading, config."""

from unifi_mcp_shared.config import load_yaml_config, setup_logging
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
from unifi_mcp_shared.tool_loader import auto_load_tools

__all__ = [
    "LazyToolLoader",
    "PermissionChecker",
    "auto_load_tools",
    "build_tool_module_map",
    "create_preview",
    "load_yaml_config",
    "preview_response",
    "register_load_tools",
    "register_meta_tools",
    "setup_lazy_loading",
    "setup_logging",
    "should_auto_confirm",
    "toggle_preview",
    "update_preview",
]
