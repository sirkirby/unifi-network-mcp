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

from src.bootstrap import (
    UNIFI_TOOL_REGISTRATION_MODE,
    logger,
)  # ensures logging/env setup early
from src.jobs import get_job_status, start_async_tool

# Shared singletons
from src.runtime import (
    config,
    connection_manager,
    server,
)
from src.tool_index import register_tool, tool_index_handler
from src.utils.config_helpers import parse_config_bool
from src.utils.diagnostics import diagnostics_enabled, wrap_tool
from src.utils.lazy_tool_loader import setup_lazy_loading
from src.utils.meta_tools import register_load_tools, register_meta_tools
from src.utils.permissions import parse_permission  # noqa: E402
from src.utils.tool_loader import auto_load_tools

# Use the original FastMCP tool decorator (saved in runtime.py before wrapping)
_original_tool_decorator = getattr(server, "_original_tool", server.tool)


def permissioned_tool(*d_args, **d_kwargs):  # acts like @server.tool
    """Decorator that only registers the tool if permission allows."""

    tool_name = d_kwargs.get("name") if d_kwargs.get("name") else (d_args[0] if d_args else None)

    category = d_kwargs.pop("permission_category", None)
    action = d_kwargs.pop("permission_action", None)

    def decorator(func):
        """Inner decorator actually registering the tool if allowed."""
        nonlocal category, action, tool_name

        # Extract tool metadata for registry (before permission check)
        # Use the provided name or fall back to function name
        if not tool_name:
            tool_name = getattr(func, "__name__", "<unknown>")

        description = d_kwargs.get("description", "")
        input_schema = d_kwargs.get("input_schema")
        output_schema = d_kwargs.get("output_schema")

        # If no explicit input_schema, try to infer from function annotations
        if input_schema is None:
            try:
                import inspect

                sig = inspect.signature(func)
                properties = {}
                required = []

                for param_name, param in sig.parameters.items():
                    # Skip 'self', 'cls', and kwargs/args
                    if param_name in ("self", "cls") or param.kind in (
                        inspect.Parameter.VAR_POSITIONAL,
                        inspect.Parameter.VAR_KEYWORD,
                    ):
                        continue

                    # Extract type hint
                    param_type = "string"  # default
                    if param.annotation != inspect.Parameter.empty:
                        ann = param.annotation
                        # Handle generic types like Dict[str, Any], List[str]
                        from typing import get_origin

                        origin = get_origin(ann)
                        # Basic type mapping (check origin first for generics)
                        if origin is dict or ann in (dict, "dict"):
                            param_type = "object"
                        elif origin is list or ann in (list, "list"):
                            param_type = "array"
                        elif ann in (int, "int"):
                            param_type = "integer"
                        elif ann in (bool, "bool"):
                            param_type = "boolean"
                        elif ann in (float, "float"):
                            param_type = "number"

                    properties[param_name] = {"type": param_type}

                    # If no default value, mark as required
                    if param.default == inspect.Parameter.empty:
                        required.append(param_name)

                input_schema = {
                    "type": "object",
                    "properties": properties,
                }
                if required:
                    input_schema["required"] = required

            except Exception as exc:
                logger.debug(f"Could not infer input schema for {tool_name}: {exc}")
                input_schema = {"type": "object", "properties": {}}

        # Fast path: no permissions requested, just register.
        if not category or not action:
            # Register in tool index
            register_tool(
                name=tool_name,
                description=description,
                input_schema=input_schema,
                output_schema=output_schema,
            )
            return _original_tool_decorator(*d_args, **d_kwargs)(func)

        # ALWAYS register in tool index (for discovery via unifi_tool_index)
        # This ensures manifest generation includes ALL tools regardless of permissions
        register_tool(
            name=tool_name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
        )

        # Check permissions for MCP server registration
        try:
            allowed = parse_permission(config.permissions, category, action)
        except Exception as exc:  # mis‑config should not crash server
            logger.error("Permission check failed for tool %s: %s", tool_name, exc)
            allowed = False

        if allowed:
            # Permission granted - register with MCP server
            wrapped = (
                wrap_tool(func, tool_name or getattr(func, "__name__", "<tool>")) if diagnostics_enabled() else func
            )
            return _original_tool_decorator(*d_args, **d_kwargs)(wrapped)

        # Permission denied - tool is in index but not callable via MCP
        logger.info(
            "[permissions] Skipping MCP registration of tool '%s' (category=%s, action=%s)",
            tool_name,
            category,
            action,
        )
        # Return original function (unregistered with MCP) for import side-effects/testing
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
        print(f"Logging in main_async() failed: {e}", file=sys.stderr)  # Fallback
    # ---- END VERY EARLY ASYNC LOG TEST ----

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

    # Config is now loaded globally (from src.runtime -> src.bootstrap)
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
        )

        from src.utils.lazy_tool_loader import TOOL_MODULE_MAP

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

    # Run stdio always; optionally run HTTP SSE based on config flag
    host = config.server.get("host", "0.0.0.0")
    port = int(config.server.get("port", 3000))
    http_cfg = config.server.get("http", {})
    http_enabled = parse_config_bool(http_cfg.get("enabled", False))

    # Only the main container process (PID 1) should bind the HTTP SSE port,
    # unless http.force=true is set in config (for local development/testing).
    force_http = parse_config_bool(http_cfg.get("force", False))
    is_main_container_process = os.getpid() == 1
    if http_enabled and not is_main_container_process and not force_http:
        logger.info(
            "HTTP SSE enabled in config but skipped in exec session (PID %s != 1). "
            "Set UNIFI_MCP_HTTP_FORCE=true to override.",
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
                logger.info(f"Starting FastMCP HTTP SSE server on {host}:{port} ...")
                server.settings.host = host
                server.settings.port = port

                # Redirect uvicorn access logs to stderr to prevent stdout conflicts
                # when running alongside stdio transport (stdout is used for JSON-RPC)
                uvicorn.config.LOGGING_CONFIG["handlers"]["access"]["stream"] = "ext://sys.stderr"

                await server.run_sse_async()
                logger.info("HTTP SSE started via run_sse_async() using server.settings host/port.")
            except Exception as http_e:
                logger.error(f"HTTP SSE server failed to start: {http_e}")
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
    # ---- VERY EARLY LOG TEST ----
    try:
        from src.bootstrap import logger as bootstrap_logger

        bootstrap_logger.critical("SYNCHRONOUS main() FUNCTION ENTERED - TEST MESSAGE")
    except Exception as e:
        print(f"Logging in main() failed: {e}", file=sys.stderr)  # Fallback
    # ---- END VERY EARLY LOG TEST ----

    logger.debug("Starting main()")  # This uses the logger from bootstrap via global scope
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
