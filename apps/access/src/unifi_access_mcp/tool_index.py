"""Tool index and registry — re-exported from shared package."""

from pathlib import Path

from unifi_mcp_shared.permissions import PermissionChecker
from unifi_mcp_shared.tool_index import (
    TOOL_REGISTRY,
    ToolMetadata,
    register_tool,
)
from unifi_mcp_shared.tool_index import (
    get_tool_index as _get_tool_index,
)


def get_tool_index():
    """Get the complete tool index, using access server's registration mode and manifest."""
    try:
        from unifi_access_mcp.bootstrap import UNIFI_TOOL_REGISTRATION_MODE

        registration_mode = UNIFI_TOOL_REGISTRATION_MODE
    except ImportError:
        registration_mode = "lazy"

    from unifi_access_mcp.categories import ACCESS_CATEGORY_MAP
    from unifi_access_mcp.runtime import config

    checker = PermissionChecker(category_map=ACCESS_CATEGORY_MAP, permissions=config.permissions)
    manifest_path = Path(__file__).parent / "tools_manifest.json"
    return _get_tool_index(
        registration_mode=registration_mode,
        manifest_path=manifest_path,
        permission_checker=checker,
    )


async def tool_index_handler(args=None):
    """Handler for the access_tool_index tool."""
    return get_tool_index()


__all__ = ["TOOL_REGISTRY", "ToolMetadata", "get_tool_index", "register_tool", "tool_index_handler"]
