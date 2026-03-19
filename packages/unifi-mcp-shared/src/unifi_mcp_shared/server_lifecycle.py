"""Shared server lifecycle helpers for MCP servers.

Consolidates the boilerplate that every MCP server main.py repeats:
- asyncio global exception handler
- log-level application from config
- synchronous ``main()`` entry-point wrapper
- ``sys.modules`` registration for import safety
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any, Callable, Coroutine


def install_asyncio_exception_handler(logger: logging.Logger) -> None:
    """Install a global asyncio exception handler that logs full context.

    Catches unhandled exceptions in asyncio tasks/futures and logs them with
    traceback information via *logger*.  Must be called from within a running
    event loop (i.e. inside an ``async`` function).
    """
    loop = asyncio.get_event_loop()

    def _handle(loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
        exc = context.get("exception", context.get("message", "Unknown error"))
        parts = [f"Global asyncio exception handler caught: {exc}"]
        if context.get("future"):
            parts.append(f"Future: {context['future']}")
        if context.get("handle"):
            parts.append(f"Handle: {context['handle']}")
        logger.error("\n".join(parts))
        if context.get("exception"):
            logger.error("Original traceback for global asyncio exception:", exc_info=context["exception"])

    loop.set_exception_handler(_handle)
    logger.info("Global asyncio exception handler set.")


def apply_log_level(config: Any, logger_name: str) -> None:
    """Apply the ``log_level`` setting from *config* to the named logger.

    Reads ``config.server.get("log_level", "INFO")`` and sets the level on
    ``logging.getLogger(logger_name)``.
    """
    log_level = config.server.get("log_level", "INFO").upper()
    logging.getLogger(logger_name).setLevel(getattr(logging, log_level, logging.INFO))


def run_main(main_async: Callable[[], Coroutine], *, logger: logging.Logger) -> None:
    """Synchronous entry-point wrapper shared by all MCP servers.

    Runs *main_async* via ``asyncio.run`` with graceful handling of
    ``KeyboardInterrupt`` and unhandled exceptions.
    """
    logger.debug("Starting main()")
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Server stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.exception("Unhandled exception during server run (from asyncio.run): %s", e)
    finally:
        logger.info("Server process exiting.")


def register_main_module(module_name: str) -> None:
    """Register the current ``__main__`` module under *module_name*.

    Ensures that ``import <module_name>`` works even when the file is executed
    directly as ``__main__``.  Harmless if the module is already registered.
    """
    if module_name not in sys.modules:
        # The caller's module is the one that invoked us — use __main__
        main_mod = sys.modules.get("__main__")
        if main_mod is not None:
            sys.modules[module_name] = main_mod
