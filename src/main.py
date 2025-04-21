# ruff: noqa: E402
"""Main entry‑point for the UniFi‑Network MCP server.

Responsibilities:
• configure permissions wrappers
• initialise UniFi connection
• start FastMCP (stdio) + optional Uvicorn SSE app
"""

import asyncio
import logging
import traceback
import uvicorn
import sys

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

# Load config globally via bootstrap helper
config = config
logger.info("Loaded configuration globally.")

# --- Global Connection and Managers --- 
# Initialize connection manager globally after config is loaded
connection_manager = connection_manager
logger.info("Created global ConnectionManager instance.")

# Instantiate other managers globally, using the global connection_manager
client_manager = client_manager
device_manager = device_manager
stats_manager = stats_manager
qos_manager = qos_manager
vpn_manager = vpn_manager
network_manager = network_manager
system_manager = system_manager
firewall_manager = firewall_manager
logger.info("Created global Manager instances.")

# Dynamic tool loader helper already imported above

async def setup_server():
    """Sets up the MCP server: connects to Unifi, handles tool registration (implicitly)."""
    # Config is now loaded globally
    log_level = config.server.get("log_level", "INFO").upper()
    # Ensure logging is configured (might be redundant if already set)
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO), force=True) 
    logger.info(f"Log level set to {log_level}")

    # ConnectionManager is now global, just initialize the connection
    logger.info("Initializing global Unifi connection...")
    if not await connection_manager.initialize():
        logger.error("Failed to connect to Unifi Controller. Tool functionality may be impaired.")
        # Decide if we should exit or continue with limited functionality
    else:
        logger.info("Global Unifi connection initialized successfully.")
    
    # Load tool modules after connection is established
    auto_load_tools()
    
    # List all registered tools for debugging - proper place to await the async method
    try:
        tools = await server.list_tools()
        logger.info(f"Registered tools: {[tool.name for tool in tools]}")
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
    
    logger.info("Tool registration handled by module imports.")

    logger.info("Handing off to FastMCP stdio transport (blocking run)...")
    try:
        await server.run_stdio_async()
    except Exception as e:
        logger.error(f"Error running FastMCP stdio server: {e}")
        logger.error(traceback.format_exc())
        raise

    logger.info("Server setup complete.")
    # Since server.run_stdio_async() in setup_server() is blocking and handles all incoming
    # requests via stdio, we do not need to start a separate Uvicorn HTTP server.
    logger.info("FastMCP stdio transport active; skipping launch of Uvicorn.")
    return

def main():
    """Run the setup and then start the server with uvicorn."""
    logger.debug("Starting main()")
    try:
        # Run the setup tasks first
        logger.info("Starting server setup…")
        asyncio.run(setup_server())
        logger.info("Server setup complete.")

        # Read host/port/log_level for uvicorn
        host = config.server.host
        port = config.server.port
        log_level = config.server.get("log_level", "info").lower()

        logger.info(f"Starting Uvicorn server on {host}:{port}...")
        
        try:
            # Use the sse_app() method to get the Starlette app, not server.app
            starlette_app = server.sse_app()
            uvicorn.run(starlette_app, host=host, port=port, log_level=log_level)
            # Note: uvicorn.run is blocking, code after this won't run until server stops.
        except Exception as e:
            logger.error(f"Error running Uvicorn server: {e}")
            logger.error(traceback.format_exc())
            raise

    except KeyboardInterrupt:
        logger.info("Server stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.exception("Unhandled exception in main: %s", e)
    finally:
        logger.info("Server process exiting.") # Log when the main function exits

# Ensure other modules can `import src.main` even when this file is executed as __main__
if "src.main" not in sys.modules:
    sys.modules["src.main"] = sys.modules[__name__]

if __name__ == "__main__":
    main()