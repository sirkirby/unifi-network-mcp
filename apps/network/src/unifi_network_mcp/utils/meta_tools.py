"""Meta-tools registration helper (network app wrapper).

Re-exports from unifi_mcp_shared.meta_tools. The network app's main.py
passes TOOL_MODULE_MAP when calling register_load_tools.
"""

from unifi_mcp_shared.meta_tools import register_load_tools, register_meta_tools

__all__ = ["register_load_tools", "register_meta_tools"]
