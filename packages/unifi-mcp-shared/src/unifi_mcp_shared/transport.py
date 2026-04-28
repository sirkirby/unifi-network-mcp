"""Shared transport lifecycle management for MCP servers.

Handles running stdio and HTTP transports concurrently with proper lifecycle
coupling: when one transport exits, the other is cancelled. This prevents
orphaned processes when a stdio client disconnects while the HTTP server is
still listening.

Also catches ``SystemExit`` from uvicorn bind failures (e.g. port conflict)
so that a failed HTTP transport does not kill the stdio connection.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING, Any

from unifi_core.config_helpers import parse_config_bool

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

VALID_HTTP_TRANSPORTS = {"streamable-http", "sse"}
_TRANSPORT_LABELS = {"streamable-http": "Streamable HTTP", "sse": "HTTP SSE"}


def resolve_http_config(
    server_cfg: Any,
    *,
    default_port: int = 3000,
    logger: logging.Logger,
) -> tuple[bool, str, str, int]:
    """Parse HTTP transport settings from the server config block.

    Returns ``(http_enabled, http_transport, host, port)`` with validation
    applied (invalid transport falls back to ``streamable-http``, PID-1 check
    may disable HTTP).
    """
    host = server_cfg.get("host", "0.0.0.0")
    port = int(server_cfg.get("port", default_port))
    http_cfg = server_cfg.get("http", {})
    http_enabled = parse_config_bool(http_cfg.get("enabled", False))

    http_transport = http_cfg.get("transport", "streamable-http")
    if isinstance(http_transport, str):
        http_transport = http_transport.lower()
    if http_transport not in VALID_HTTP_TRANSPORTS:
        logger.warning(
            "Invalid UNIFI_MCP_HTTP_TRANSPORT: '%s'. Defaulting to 'streamable-http'.",
            http_transport,
        )
        http_transport = "streamable-http"

    transport_label = _TRANSPORT_LABELS[http_transport]

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

    return http_enabled, http_transport, host, port


async def run_transports(
    *,
    server: FastMCP,
    http_enabled: bool,
    host: str,
    port: int,
    http_transport: str,
    logger: logging.Logger,
    protocol_version: str = "v1",
) -> None:
    """Run stdio (always) and optionally HTTP, with coupled lifecycles.

    When both transports are active, uses ``asyncio.wait(FIRST_COMPLETED)``
    so that when either transport exits the other is cancelled.  This ensures
    the process terminates cleanly when the stdio client disconnects instead
    of being kept alive by the HTTP server.

    ``SystemExit`` raised by uvicorn on port-bind failures is caught inside
    ``run_http`` so it does not propagate and kill the stdio transport.
    """
    # Future: when MCP SDK v2 changes the transport API, branch here:
    # if protocol_version == "v2":
    #     return await _run_transports_v2(server, ...)

    async def run_stdio() -> None:
        logger.info("Starting FastMCP stdio server ...")
        await server.run_stdio_async()

    if not http_enabled:
        try:
            await run_stdio()
            logger.info("FastMCP stdio server exited.")
        except Exception as e:
            logger.error("Error running FastMCP stdio server: %s", e, exc_info=True)
            raise
        return

    transport_label = _TRANSPORT_LABELS.get(http_transport, http_transport)

    async def run_http() -> None:
        try:
            logger.info("Starting FastMCP %s server on %s:%s ...", transport_label, host, port)
            server.settings.host = host
            server.settings.port = port

            # Redirect uvicorn access logs to stderr to prevent stdout conflicts
            # when running alongside stdio transport (stdout is used for JSON-RPC)
            import uvicorn.config

            uvicorn.config.LOGGING_CONFIG["handlers"]["access"]["stream"] = "ext://sys.stderr"

            if http_transport == "streamable-http":
                await server.run_streamable_http_async()
            else:
                await server.run_sse_async()
            logger.info("%s server exited.", transport_label)
        except SystemExit as se:
            logger.error(
                "FastMCP %s server exited with SystemExit (code %s) — likely a port conflict on %s:%s",
                transport_label,
                se.code,
                host,
                port,
            )
        except Exception as http_e:
            logger.error("FastMCP %s server failed to start: %s", transport_label, http_e, exc_info=True)

    # When running as PID 1 (Docker container main process), stdin has no
    # client — stdio would exit immediately via EOF and cancel the HTTP
    # transport.  Run HTTP-only in this case.
    is_main_container_process = os.getpid() == 1
    if is_main_container_process:
        logger.info("Container main process (PID 1): running %s transport only.", transport_label)
        try:
            await run_http()
            logger.info("FastMCP %s server exited.", transport_label)
        except Exception as e:
            logger.error("Error running FastMCP %s server: %s", transport_label, e, exc_info=True)
            raise
        return

    # Use asyncio tasks so we can cancel HTTP when stdio exits (or vice versa).
    # Without this, the HTTP server keeps the process alive as an orphan after
    # the stdio client disconnects.
    stdio_task = asyncio.create_task(run_stdio(), name="stdio")
    http_task = asyncio.create_task(run_http(), name="http")

    try:
        done, pending = await asyncio.wait(
            [stdio_task, http_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        # Whichever finished first — cancel the other and let it clean up
        for task in pending:
            logger.info("Cancelling %s transport (other transport exited).", task.get_name())
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        # Re-raise if the completed task had an exception
        for task in done:
            if not task.cancelled() and task.exception():
                raise task.exception()
        logger.info("FastMCP servers exited.")
    except Exception as e:
        logger.error("Error running FastMCP servers: %s", e, exc_info=True)
        raise
