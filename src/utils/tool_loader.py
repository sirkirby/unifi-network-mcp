import importlib
import logging
import pkgutil
from types import ModuleType
from typing import List, Optional

logger = logging.getLogger("unifi-network-mcp")


def auto_load_tools(
    base_package: str = "src.tools",
    enabled_categories: Optional[List[str]] = None,
    enabled_tools: Optional[List[str]] = None,
    server=None,
) -> None:
    """Dynamically import tool modules from *base_package*.

    Importing each module triggers the `@server.tool` decorators inside them,
    which registers tools with the FastMCP server.

    Args:
        base_package: The package containing tool modules
        enabled_categories: If set, only load modules matching these category names
                           (e.g., ["clients", "devices", "system"])
        enabled_tools: If set, load all modules but remove tools not in this list
                      (requires server parameter)
        server: FastMCP server instance (required if enabled_tools is set)
    """
    try:
        tools_pkg: ModuleType = importlib.import_module(base_package)
    except ModuleNotFoundError as exc:
        logger.error(f"Tool package '{base_package}' not found: {exc}")
        return

    # Normalize enabled_categories to a set for fast lookup
    categories_filter = set(enabled_categories) if enabled_categories else None

    if categories_filter:
        logger.info(f"Auto-loading MCP tool modules (filtered by categories: {list(categories_filter)})")
    elif enabled_tools:
        logger.info(f"Auto-loading MCP tool modules (will filter to {len(enabled_tools)} specific tools)")
    else:
        logger.info("Auto-loading MCP tool modules (all tools)")

    loaded_modules = []
    for mod_info in pkgutil.walk_packages(tools_pkg.__path__, tools_pkg.__name__ + "."):
        mod_name = mod_info.name
        # Get the module's simple name (e.g., "clients" from "src.tools.clients")
        simple_name = mod_name.rsplit(".", 1)[-1]

        # Skip private modules (starting with _)
        if simple_name.startswith("_"):
            continue

        # Filter by category if specified
        if categories_filter and simple_name not in categories_filter:
            logger.debug(f"Skipping module '{mod_name}' (not in enabled_categories)")
            continue

        try:
            importlib.import_module(mod_name)
            loaded_modules.append(simple_name)
            logger.debug(f"Imported tool module: {mod_name}")
        except Exception as exc:
            # Keep going even if one module fails so the rest still load
            logger.warning(f"Failed to import tool module '{mod_name}': {exc}")

    logger.info(f"Loaded {len(loaded_modules)} tool modules: {loaded_modules}")

    # If enabled_tools is specified, remove any tools not in the list
    if enabled_tools and server:
        enabled_set = set(enabled_tools)
        # Always keep meta-tools
        meta_tools = {"unifi_tool_index", "unifi_execute", "unifi_batch", "unifi_batch_status", "unifi_load_tools"}
        enabled_set.update(meta_tools)

        try:
            import asyncio

            async def filter_tools():
                tools = await server.list_tools()
                removed = []
                for tool in tools:
                    if tool.name not in enabled_set:
                        try:
                            server.remove_tool(tool.name)
                            removed.append(tool.name)
                        except Exception as e:
                            logger.warning(f"Failed to remove tool '{tool.name}': {e}")
                if removed:
                    logger.info(f"Removed {len(removed)} tools not in enabled_tools list")
                    logger.debug(f"Removed tools: {removed}")

            # Run the async filter
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(filter_tools())
            else:
                loop.run_until_complete(filter_tools())
        except Exception as e:
            logger.warning(f"Failed to filter tools by enabled_tools: {e}")

    logger.info("Finished auto-loading MCP tool modules")
