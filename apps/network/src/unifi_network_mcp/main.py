# ruff: noqa: E402
"""Main entry‑point for the UniFi‑Network MCP server.

Responsibilities:
• configure permissions wrappers
• initialise UniFi connection
• start FastMCP (stdio)
"""

import asyncio
import logging
import os
import sys
import traceback

import uvicorn.config

from unifi_mcp_shared.meta_tools import register_load_tools, register_meta_tools
from unifi_mcp_shared.permissions import PermissionChecker
from unifi_mcp_shared.tool_loader import auto_load_tools
from unifi_network_mcp.bootstrap import (
    UNIFI_TOOL_REGISTRATION_MODE,
    logger,
)  # ensures logging/env setup early
from unifi_network_mcp.categories import NETWORK_CATEGORY_MAP, TOOL_MODULE_MAP, setup_lazy_loading
from unifi_network_mcp.jobs import get_job_status, start_async_tool

# Shared singletons
from unifi_network_mcp.runtime import (
    config,
    connection_manager,
    server,
)
from unifi_network_mcp.tool_index import register_tool, tool_index_handler
from unifi_network_mcp.utils.config_helpers import parse_config_bool
from unifi_network_mcp.utils.diagnostics import diagnostics_enabled, wrap_tool

# Use the original FastMCP tool decorator (saved in runtime.py before wrapping)
_original_tool_decorator = getattr(server, "_original_tool", server.tool)

# Shared permission checker instance for the permissioned_tool decorator
permission_checker = PermissionChecker(category_map=NETWORK_CATEGORY_MAP, permissions=config.permissions)


from unifi_mcp_shared.permissioned_tool import create_permissioned_tool

permissioned_tool = create_permissioned_tool(
    original_tool_decorator=_original_tool_decorator,
    permission_checker=permission_checker,
    register_tool_fn=register_tool,
    diagnostics_enabled_fn=diagnostics_enabled,
    wrap_tool_fn=wrap_tool,
    logger=logger,
)


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
# ConnectionManager is instantiated globally by unifi_network_mcp.runtime import
logger.info("Using global ConnectionManager instance.")

# Other Managers are instantiated globally by unifi_network_mcp.runtime import
logger.info("Using global Manager instances.")

# Dynamic tool loader helper already imported above


async def main_async():
    """Main asynchronous function to setup and run the server."""

    # --- Add asyncio global exception handler ---
    loop = asyncio.get_event_loop()

    def handle_asyncio_exception(loop, context):
        exc = context.get("exception", context["message"])
        log_message = f"Global asyncio exception handler caught: {exc}"
        if "future" in context and context["future"]:
            log_message += f"\nFuture: {context['future']}"
        if "handle" in context and context["handle"]:
            log_message += f"\nHandle: {context['handle']}"
        logger.error(log_message)
        if context.get("exception"):
            orig_traceback = "".join(
                traceback.format_exception(
                    type(context["exception"]),
                    context["exception"],
                    context["exception"].__traceback__,
                )
            )
            logger.error(f"Original traceback for global asyncio exception:\n{orig_traceback}")

    loop.set_exception_handler(handle_asyncio_exception)
    logger.info("Global asyncio exception handler set.")
    # --- End asyncio global exception handler ---

    # Config is now loaded globally (from unifi_network_mcp.runtime -> unifi_network_mcp.bootstrap)
    log_level = config.server.get("log_level", "INFO").upper()
    # Ensure logging is configured (might be redundant if already set by bootstrap)
    # but this ensures the level is applied if changed post-bootstrap.
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO), force=True)  # Use default format
    logger.info(f"Log level set to {log_level} in main_async.")

    # Initialize the global Unifi connection
    logger.info("Initializing global Unifi connection from main_async...")
    if not await connection_manager.initialize():
        logger.error("Failed to connect to Unifi Controller from main_async. Tool functionality may be impaired.")
    else:
        logger.info("Global Unifi connection initialized successfully from main_async.")

    # Register meta-tools first (always available regardless of mode)
    register_meta_tools(
        server=server,
        tool_decorator=_original_tool_decorator,
        tool_index_handler=tool_index_handler,
        start_async_tool=start_async_tool,
        get_job_status=get_job_status,
        register_tool=register_tool,
    )

    # Load full tool set based on registration mode
    if UNIFI_TOOL_REGISTRATION_MODE == "meta_only":
        logger.info("🔍 Tool registration mode: meta_only")
        logger.info("   Meta-tools: unifi_tool_index, unifi_execute, unifi_batch, unifi_batch_status")
        logger.info("   Use unifi_execute to run any tool discovered via unifi_tool_index")
        logger.info("   To load all tools directly: set UNIFI_TOOL_REGISTRATION_MODE=eager")

        # Setup lazy loading interceptor so unifi_execute/unifi_batch can load tools on demand
        setup_lazy_loading(server, _original_tool_decorator)

        logger.info(f"   On-demand loader ready - {len(TOOL_MODULE_MAP)} tools available via unifi_execute")
    elif UNIFI_TOOL_REGISTRATION_MODE == "lazy":
        logger.info("⚡ Tool registration mode: lazy")
        logger.info("   Meta-tools: unifi_tool_index, unifi_execute, unifi_batch, unifi_batch_status, unifi_load_tools")
        logger.info("   Use unifi_execute to run any tool - works with all clients")

        # Setup lazy loading interceptor
        lazy_loader = setup_lazy_loading(server, _original_tool_decorator)

        # Register unifi_load_tools meta-tool (requires lazy_loader)
        register_load_tools(
            server=server,
            tool_decorator=_original_tool_decorator,
            lazy_loader=lazy_loader,
            register_tool=register_tool,
            tool_module_map=TOOL_MODULE_MAP,
        )

        logger.info(f"   Lazy loader ready - {len(TOOL_MODULE_MAP)} tools available on-demand")
    else:  # eager (default)
        logger.info("📚 Tool registration mode: eager")

        # Check for tool filtering config
        enabled_categories = config.server.get("enabled_categories")
        enabled_tools = config.server.get("enabled_tools")

        # Parse from comma-separated string if from env var
        if isinstance(enabled_categories, str) and enabled_categories not in ("null", ""):
            enabled_categories = [c.strip() for c in enabled_categories.split(",")]
        elif enabled_categories in (None, "null", ""):
            enabled_categories = None

        if isinstance(enabled_tools, str) and enabled_tools not in ("null", ""):
            enabled_tools = [t.strip() for t in enabled_tools.split(",")]
        elif enabled_tools in (None, "null", ""):
            enabled_tools = None

        if enabled_categories:
            logger.info(f"   Filtering by categories: {enabled_categories}")
        elif enabled_tools:
            logger.info(f"   Filtering to {len(enabled_tools)} specific tools")
        else:
            logger.info("   All tools registered (no filtering)")

        auto_load_tools(
            base_package="unifi_network_mcp.tools",
            enabled_categories=enabled_categories,
            enabled_tools=enabled_tools,
            server=server,
        )

    # List all registered tools for debugging
    try:
        tools = await server.list_tools()
        logger.info(f"Registered tools in main_async: {[tool.name for tool in tools]}")
    except Exception as e:
        logger.error(f"Error listing tools in main_async: {e}")

    # Run stdio always; optionally run HTTP based on config flag
    host = config.server.get("host", "0.0.0.0")
    port = int(config.server.get("port", 3000))
    http_cfg = config.server.get("http", {})
    http_enabled = parse_config_bool(http_cfg.get("enabled", False))

    # Validate HTTP transport selection
    http_transport = http_cfg.get("transport", "streamable-http")
    if isinstance(http_transport, str):
        http_transport = http_transport.lower()
    VALID_HTTP_TRANSPORTS = {"streamable-http", "sse"}
    if http_transport not in VALID_HTTP_TRANSPORTS:
        logger.warning(
            "Invalid UNIFI_MCP_HTTP_TRANSPORT: '%s'. Defaulting to 'streamable-http'.",
            http_transport,
        )
        http_transport = "streamable-http"

    transport_label = "Streamable HTTP" if http_transport == "streamable-http" else "HTTP SSE"

    # Only the main container process (PID 1) should bind the HTTP port,
    # unless http.force=true is set in config (for local development/testing).
    force_http = parse_config_bool(http_cfg.get("force", False))
    is_main_container_process = os.getpid() == 1
    if http_enabled and not is_main_container_process and not force_http:
        logger.info(
            "%s enabled in config but skipped in exec session (PID %s != 1). "
            "Set UNIFI_MCP_HTTP_FORCE=true to override.",
            transport_label,
            os.getpid(),
        )
        http_enabled = False

    async def run_stdio():
        logger.info("Starting FastMCP stdio server ...")
        await server.run_stdio_async()

    tasks = [run_stdio()]
    if http_enabled:

        async def run_http():
            try:
                logger.info(f"Starting FastMCP {transport_label} server on {host}:{port} ...")
                server.settings.host = host
                server.settings.port = port

                # Redirect uvicorn access logs to stderr to prevent stdout conflicts
                # when running alongside stdio transport (stdout is used for JSON-RPC)
                uvicorn.config.LOGGING_CONFIG["handlers"]["access"]["stream"] = "ext://sys.stderr"

                if http_transport == "streamable-http":
                    await server.run_streamable_http_async()
                else:
                    await server.run_sse_async()
                logger.info(f"{transport_label} server exited.")
            except Exception as http_e:
                logger.error(f"FastMCP {transport_label} server failed to start: {http_e}")
                logger.error(traceback.format_exc())

        tasks.append(run_http())

    try:
        await asyncio.gather(*tasks)
        logger.info("FastMCP servers exited.")
    except Exception as e:
        logger.error(f"Error running FastMCP servers from main_async: {e}")
        logger.error(traceback.format_exc())
        raise


def main():
    """Synchronous entry point."""
    logger.debug("Starting main()")  # This uses the logger from bootstrap via global scope
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Server stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.exception("Unhandled exception during server run (from asyncio.run): %s", e)
    finally:
        logger.info("Server process exiting.")


# Ensure other modules can `import unifi_network_mcp.main` even when this file is executed as __main__
# --- This block might not be strictly necessary depending on imports, but harmless ---
if "unifi_network_mcp.main" not in sys.modules:
    sys.modules["unifi_network_mcp.main"] = sys.modules[__name__]
# --- End potentially unnecessary block ---

if __name__ == "__main__":
    main()
