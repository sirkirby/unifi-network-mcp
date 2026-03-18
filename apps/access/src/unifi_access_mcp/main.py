# ruff: noqa: E402
"""Main entry-point for the UniFi-Access MCP server.

Responsibilities:
- configure permissions wrappers
- initialise UniFi Access connection
- start FastMCP (stdio)
"""

import asyncio
import logging
import os
import sys

import uvicorn.config

from unifi_access_mcp.bootstrap import (
    UNIFI_TOOL_REGISTRATION_MODE,
    logger,
)  # ensures logging/env setup early
from unifi_access_mcp.categories import ACCESS_CATEGORY_MAP, TOOL_MODULE_MAP, setup_lazy_loading
from unifi_access_mcp.jobs import get_job_status, start_async_tool

# Shared singletons
from unifi_access_mcp.runtime import (
    config,
    connection_manager,
    event_manager,
    server,
)
from unifi_access_mcp.tool_index import register_tool, tool_index_handler
from unifi_access_mcp.utils.config_helpers import parse_config_bool
from unifi_access_mcp.utils.diagnostics import diagnostics_enabled, wrap_tool
from unifi_mcp_shared.meta_tools import register_load_tools, register_meta_tools
from unifi_mcp_shared.permissions import PermissionChecker
from unifi_mcp_shared.tool_loader import auto_load_tools

# Use the original FastMCP tool decorator (saved in runtime.py before wrapping)
_original_tool_decorator = getattr(server, "_original_tool", server.tool)

# Shared permission checker instance for the permissioned_tool decorator
permission_checker = PermissionChecker(category_map=ACCESS_CATEGORY_MAP, permissions=config.permissions)


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

logger.debug("Access MCP server module loaded; singletons initialised.")


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
            logger.error("Original traceback for global asyncio exception:", exc_info=context["exception"])

    loop.set_exception_handler(handle_asyncio_exception)
    logger.info("Global asyncio exception handler set.")
    # --- End asyncio global exception handler ---

    # Apply log level from config (bootstrap already set up handlers)
    log_level = config.server.get("log_level", "INFO").upper()
    logging.getLogger("unifi-access-mcp").setLevel(getattr(logging, log_level, logging.INFO))

    # Initialize the global Access connection
    logger.info("Initializing global Access connection from main_async...")
    if not await connection_manager.initialize():
        logger.error("Failed to connect to UniFi Access. Tool functionality may be impaired.")
    else:
        logger.info("Global Access connection initialized successfully from main_async.")

        # Start the websocket event listener if enabled and connection succeeded
        ws_enabled_raw = config.access.events.get("websocket_enabled", True) if hasattr(config, "access") else True
        ws_enabled = parse_config_bool(ws_enabled_raw)
        if ws_enabled:
            try:
                event_manager.set_server(server)
                # TODO: Implement websocket event listening for Access
                logger.info("Access event websocket listener not yet implemented.")
            except Exception as ws_exc:
                logger.error(
                    "Failed to start event websocket listener: %s. "
                    "Real-time events will be unavailable; REST queries still work.",
                    ws_exc,
                    exc_info=True,
                )
        else:
            logger.info("Access event websocket disabled via config.")

    # ---- Register MCP resources ----
    # Resources are registered by importing their modules (decorator-based).
    # Import here so they are available regardless of tool registration mode.
    try:
        import unifi_access_mcp.resources.events  # noqa: F401

        logger.info("MCP resources registered (events).")
    except Exception as res_exc:
        logger.error("Failed to register MCP resources: %s", res_exc, exc_info=True)

    # Register meta-tools first (always available regardless of mode)
    register_meta_tools(
        server=server,
        tool_decorator=_original_tool_decorator,
        tool_index_handler=tool_index_handler,
        start_async_tool=start_async_tool,
        get_job_status=get_job_status,
        register_tool=register_tool,
        prefix="access",
        server_label="UniFi Access",
    )

    # Load full tool set based on registration mode
    if UNIFI_TOOL_REGISTRATION_MODE == "meta_only":
        logger.info("Tool registration mode: meta_only")
        logger.info("   Meta-tools: access_tool_index, access_execute, access_batch, access_batch_status")
        logger.info("   Use access_execute to run any tool discovered via access_tool_index")
        logger.info("   To load all tools directly: set UNIFI_TOOL_REGISTRATION_MODE=eager")

        # Setup lazy loading interceptor so access_execute/access_batch can load tools on demand
        setup_lazy_loading(server, _original_tool_decorator)

        logger.info("   On-demand loader ready - %d tools available via access_execute", len(TOOL_MODULE_MAP))
    elif UNIFI_TOOL_REGISTRATION_MODE == "lazy":
        logger.info("Tool registration mode: lazy")
        logger.info(
            "   Meta-tools: access_tool_index, access_execute, access_batch, access_batch_status, access_load_tools"
        )
        logger.info("   Use access_execute to run any tool - works with all clients")

        # Setup lazy loading interceptor
        lazy_loader = setup_lazy_loading(server, _original_tool_decorator)

        # Register access_load_tools meta-tool (requires lazy_loader)
        register_load_tools(
            server=server,
            tool_decorator=_original_tool_decorator,
            lazy_loader=lazy_loader,
            register_tool=register_tool,
            tool_module_map=TOOL_MODULE_MAP,
            prefix="access",
            server_label="UniFi Access",
        )

        logger.info("   Lazy loader ready - %d tools available on-demand", len(TOOL_MODULE_MAP))
    else:  # eager (default)
        logger.info("Tool registration mode: eager")

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
            logger.info("   Filtering by categories: %s", enabled_categories)
        elif enabled_tools:
            logger.info("   Filtering to %d specific tools", len(enabled_tools))
        else:
            logger.info("   All tools registered (no filtering)")

        auto_load_tools(
            base_package="unifi_access_mcp.tools",
            enabled_categories=enabled_categories,
            enabled_tools=enabled_tools,
            server=server,
        )

    # List all registered tools for debugging
    try:
        tools = await server.list_tools()
        logger.debug("Registered tools: %s", [tool.name for tool in tools])
    except Exception as e:
        logger.debug("Error listing tools: %s", e)

    # Run stdio always; optionally run HTTP based on config flag
    host = config.server.get("host", "0.0.0.0")
    port = int(config.server.get("port", 3002))
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
                logger.info("Starting FastMCP %s server on %s:%s ...", transport_label, host, port)
                server.settings.host = host
                server.settings.port = port

                # Redirect uvicorn access logs to stderr to prevent stdout conflicts
                # when running alongside stdio transport (stdout is used for JSON-RPC)
                uvicorn.config.LOGGING_CONFIG["handlers"]["access"]["stream"] = "ext://sys.stderr"

                if http_transport == "streamable-http":
                    await server.run_streamable_http_async()
                else:
                    await server.run_sse_async()
                logger.info("%s server exited.", transport_label)
            except Exception as http_e:
                logger.error("FastMCP %s server failed to start: %s", transport_label, http_e, exc_info=True)

        tasks.append(run_http())

    try:
        await asyncio.gather(*tasks)
        logger.info("FastMCP servers exited.")
    except Exception as e:
        logger.error("Error running FastMCP servers: %s", e, exc_info=True)
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


# Ensure other modules can `import unifi_access_mcp.main` even when this file is executed as __main__
# --- This block might not be strictly necessary depending on imports, but harmless ---
if "unifi_access_mcp.main" not in sys.modules:
    sys.modules["unifi_access_mcp.main"] = sys.modules[__name__]
# --- End potentially unnecessary block ---

if __name__ == "__main__":
    main()
