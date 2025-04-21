import importlib
import logging
import pkgutil
from types import ModuleType

logger = logging.getLogger("unifi-network-mcp")


def auto_load_tools(base_package: str = "src.tools") -> None:
    """Dynamically import every sub‑module in *base_package*.

    Importing each module triggers the `@server.tool` decorators inside them,
    which registers tools with the FastMCP server.  This eliminates the need
    to keep a hard‑coded list of imports up to date every time a new tool file
    is added.
    """
    try:
        tools_pkg: ModuleType = importlib.import_module(base_package)
    except ModuleNotFoundError as exc:
        logger.error(f"Tool package '{base_package}' not found: {exc}")
        return

    logger.info("Auto‑loading MCP tool modules …")

    for mod_info in pkgutil.walk_packages(tools_pkg.__path__, tools_pkg.__name__ + "."):
        mod_name = mod_info.name
        # Skip private modules (starting with _)
        if mod_name.rsplit(".", 1)[-1].startswith("_"):
            continue
        try:
            importlib.import_module(mod_name)
            logger.debug(f"Imported tool module: {mod_name}")
        except Exception as exc:
            # Keep going even if one module fails so the rest still load
            logger.warning(f"Failed to import tool module '{mod_name}': {exc}")

    logger.info("Finished auto‑loading MCP tool modules") 