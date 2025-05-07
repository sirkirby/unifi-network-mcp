# ruff: noqa: E402
"""Main entry‑point for the UniFi‑Network MCP server.

Responsibilities:
• configure permissions wrappers
• initialise UniFi connection
• start FastMCP (stdio)
"""

import asyncio
import logging
import traceback
import sys # Removed uvicorn import

from src.bootstrap import logger  # ensures logging/env setup early

# Shared singletons
from src.runtime import (
    server,
    config,
    connection_manager,
    client_manager,
    device_manager,
    stats_manager,
    qos_manager,
    vpn_manager,
    network_manager,
    system_manager,
    firewall_manager,
)

from src.utils.tool_loader import auto_load_tools
from src.utils.permissions import parse_permission  # noqa: E402

_original_tool_decorator = server.tool  # keep reference to wrap later

def permissioned_tool(*d_args, **d_kwargs):  # acts like @server.tool
    """Decorator that only registers the tool if permission allows."""

    tool_name = d_kwargs.get("name") if d_kwargs.get("name") else (d_args[0] if d_args else None)

    category = d_kwargs.pop("permission_category", None)
    action = d_kwargs.pop("permission_action", None)

    def decorator(func):
        """Inner decorator actually registering the tool if allowed."""
        nonlocal category, action

        # Fast path: no permissions requested, just register.
        if not category or not action:
            return _original_tool_decorator(*d_args, **d_kwargs)(func)

        try:
            allowed = parse_permission(config.permissions, category, action)
        except Exception as exc:  # mis‑config should not crash server
            logger.error("Permission check failed for tool %s: %s", tool_name, exc)
            allowed = False

        if allowed:
            return _original_tool_decorator(*d_args, **d_kwargs)(func)

        logger.info(
            "[permissions] Skipping registration of tool '%s' (category=%s, action=%s)",
            tool_name,
            category,
            action,
        )
        return func

    return decorator

server.tool = permissioned_tool  # type: ignore

# Log server version and capabilities
try:
    import mcp
    logger.info(f"MCP Python SDK version: {getattr(mcp, '__version__', 'unknown')}")
    logger.info(f"Server methods: {dir(server)}")
    logger.info(f"Server tool methods: {[m for m in dir(server) if 'tool' in m.lower()]}")
except Exception as e:
    logger.error(f"Error inspecting server: {e}")

# Config is loaded globally via bootstrap helper
logger.info("Loaded configuration globally.")

# --- Global Connection and Managers ---
# ConnectionManager is instantiated globally by src.runtime import
logger.info("Using global ConnectionManager instance.")

# Other Managers are instantiated globally by src.runtime import
logger.info("Using global Manager instances.")

# Dynamic tool loader helper already imported above

async def main_async():
    """Main asynchronous function to setup and run the server."""

    # ---- VERY EARLY ASYNC LOG TEST ----
    try:
        from src.bootstrap import logger as bootstrap_logger_async
        bootstrap_logger_async.critical("ASYNCHRONOUS main_async() FUNCTION ENTERED - TEST MESSAGE")
    except Exception as e:
        print(f"Logging in main_async() failed: {e}", file=sys.stderr) # Fallback
    # ---- END VERY EARLY ASYNC LOG TEST ----

    # --- Add asyncio global exception handler ---
    loop = asyncio.get_event_loop()

    def handle_asyncio_exception(loop, context):
        exc = context.get("exception", context["message"])
        log_message = f"Global asyncio exception handler caught: {exc}"
        if 'future' in context and context['future']:
            log_message += f"\nFuture: {context['future']}"
        if 'handle' in context and context['handle']:
            log_message += f"\nHandle: {context['handle']}"
        logger.error(log_message)
        if context.get("exception"):
            orig_traceback = ''.join(traceback.format_exception(type(context["exception"]), context["exception"], context["exception"].__traceback__))
            logger.error(f"Original traceback for global asyncio exception:\n{orig_traceback}")

    loop.set_exception_handler(handle_asyncio_exception)
    logger.info("Global asyncio exception handler set.")
    # --- End asyncio global exception handler ---

    # Config is now loaded globally (from src.runtime -> src.bootstrap)
    log_level = config.server.get("log_level", "INFO").upper()
    # Ensure logging is configured (might be redundant if already set by bootstrap)
    # but this ensures the level is applied if changed post-bootstrap.
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO), force=True) # Use default format
    logger.info(f"Log level set to {log_level} in main_async.")

    # Initialize the global Unifi connection
    logger.info("Initializing global Unifi connection from main_async...")
    if not await connection_manager.initialize():
        logger.error("Failed to connect to Unifi Controller from main_async. Tool functionality may be impaired.")
    else:
        logger.info("Global Unifi connection initialized successfully from main_async.")

    # Load tool modules after connection is established (or attempted)
    auto_load_tools()

    # List all registered tools for debugging
    try:
        tools = await server.list_tools()
        logger.info(f"Registered tools in main_async: {[tool.name for tool in tools]}")
    except Exception as e:
        logger.error(f"Error listing tools in main_async: {e}")

    logger.info("Handing off to FastMCP stdio transport (blocking run) from main_async...")
    try:
        await server.run_stdio_async()
        logger.info("FastMCP stdio server finished gracefully from main_async.")
    except Exception as e:
        logger.error(f"Error running FastMCP stdio server from main_async: {e}")
        logger.error(traceback.format_exc()) # Log the full traceback
        raise # Reraise the exception so asyncio.run reports it and it gets logged by main()

def main():
    """Synchronous entry point."""
    # ---- VERY EARLY LOG TEST ----
    try:
        from src.bootstrap import logger as bootstrap_logger
        bootstrap_logger.critical("SYNCHRONOUS main() FUNCTION ENTERED - TEST MESSAGE")
    except Exception as e:
        print(f"Logging in main() failed: {e}", file=sys.stderr) # Fallback
    # ---- END VERY EARLY LOG TEST ----
    
    logger.debug("Starting main()") # This uses the logger from bootstrap via global scope
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Server stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.exception("Unhandled exception during server run (from asyncio.run): %s", e)
    finally:
        logger.info("Server process exiting.")

# Ensure other modules can `import src.main` even when this file is executed as __main__
# --- This block might not be strictly necessary depending on imports, but harmless ---
if "src.main" not in sys.modules:
    sys.modules["src.main"] = sys.modules[__name__]
# --- End potentially unnecessary block ---

if __name__ == "__main__":
    main()