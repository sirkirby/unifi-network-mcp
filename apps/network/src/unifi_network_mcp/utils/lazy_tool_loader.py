"""Lazy tool loader for on-demand tool registration (network app wrapper).

Thin wrapper around unifi_mcp_shared.lazy_tools that provides the network-
specific TOOL_MODULE_MAP and setup_lazy_loading/LazyToolLoader re-exports.
"""

from pathlib import Path
from typing import Callable, Dict

from unifi_mcp_shared.lazy_tools import (
    LazyToolLoader,
    build_tool_module_map,
)
from unifi_mcp_shared.lazy_tools import (
    setup_lazy_loading as _shared_setup_lazy_loading,
)

# Network-specific manifest path
_MANIFEST_PATH = Path(__file__).parent.parent / "tools_manifest.json"
_MANIFEST_FALLBACK = Path("apps/network/src/unifi_network_mcp/tools_manifest.json")


def _build_tool_module_map() -> Dict[str, str]:
    """Build tool-to-module mapping for the network app."""
    manifest = _MANIFEST_PATH if _MANIFEST_PATH.exists() else _MANIFEST_FALLBACK
    return build_tool_module_map("unifi_network_mcp.tools", manifest_path=str(manifest))


# Build the tool map at module load time
TOOL_MODULE_MAP: Dict[str, str] = _build_tool_module_map()


def setup_lazy_loading(server, tool_decorator: Callable) -> LazyToolLoader:
    """Setup lazy tool loading for the network app.

    Wraps the shared setup_lazy_loading, automatically passing TOOL_MODULE_MAP.

    Args:
        server: FastMCP server instance
        tool_decorator: The decorator function to register tools

    Returns:
        LazyToolLoader instance
    """
    return _shared_setup_lazy_loading(server, tool_decorator, TOOL_MODULE_MAP)


__all__ = [
    "TOOL_MODULE_MAP",
    "LazyToolLoader",
    "setup_lazy_loading",
    "_build_tool_module_map",
]
