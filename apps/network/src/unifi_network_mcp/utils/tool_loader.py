"""Eager tool loader (network app wrapper).

Re-exports auto_load_tools from unifi_mcp_shared.tool_loader, defaulting
base_package to the network app's tools package.
"""

from typing import List, Optional

from unifi_mcp_shared.tool_loader import auto_load_tools as _shared_auto_load_tools


def auto_load_tools(
    base_package: str = "unifi_network_mcp.tools",
    enabled_categories: Optional[List[str]] = None,
    enabled_tools: Optional[List[str]] = None,
    server=None,
) -> None:
    """Dynamically import tool modules from *base_package*.

    Thin wrapper that defaults base_package to ``"unifi_network_mcp.tools"``.
    See :func:`unifi_mcp_shared.tool_loader.auto_load_tools` for full docs.
    """
    _shared_auto_load_tools(
        base_package=base_package,
        enabled_categories=enabled_categories,
        enabled_tools=enabled_tools,
        server=server,
    )
