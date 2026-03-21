"""Tests for shared transport lifecycle management."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unifi_mcp_shared.transport import resolve_http_config, run_transports


class TestResolveHttpConfig:
    """Tests for resolve_http_config utility."""

    def _make_server_cfg(self, **overrides):
        cfg = {
            "host": "0.0.0.0",
            "port": 3000,
            "http": {"enabled": False, "force": False, "transport": "streamable-http"},
        }
        cfg.update(overrides)
        return MagicMock(**{"get.side_effect": cfg.get})

    def test_http_disabled_by_default(self):
        cfg = self._make_server_cfg()
        enabled, transport, host, port = resolve_http_config(
            cfg, default_port=3000, logger=logging.getLogger("test")
        )
        assert enabled is False

    def test_invalid_transport_falls_back(self):
        cfg = self._make_server_cfg(http={"enabled": True, "force": True, "transport": "bogus"})
        enabled, transport, host, port = resolve_http_config(
            cfg, default_port=3000, logger=logging.getLogger("test")
        )
        assert transport == "streamable-http"


class TestRunTransports:
    """Tests for transport lifecycle coupling."""

    @pytest.fixture()
    def mock_server(self):
        server = MagicMock()
        server.run_stdio_async = AsyncMock()
        server.run_streamable_http_async = AsyncMock()
        server.run_sse_async = AsyncMock()
        server.settings = MagicMock()
        return server

    @pytest.mark.asyncio
    async def test_stdio_only_when_http_disabled(self, mock_server):
        """When HTTP is disabled, only stdio runs."""
        await run_transports(
            server=mock_server,
            http_enabled=False,
            host="0.0.0.0",
            port=3000,
            http_transport="streamable-http",
            logger=logging.getLogger("test"),
        )
        mock_server.run_stdio_async.assert_awaited_once()
        mock_server.run_streamable_http_async.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_pid1_skips_stdio_runs_http_only(self, mock_server):
        """When PID is 1 (Docker container), skip stdio and run HTTP only."""
        with patch("unifi_mcp_shared.transport.os.getpid", return_value=1):
            await run_transports(
                server=mock_server,
                http_enabled=True,
                host="0.0.0.0",
                port=3000,
                http_transport="streamable-http",
                logger=logging.getLogger("test"),
            )
        mock_server.run_stdio_async.assert_not_awaited()
        mock_server.run_streamable_http_async.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_pid1_runs_sse_transport(self, mock_server):
        """PID 1 with SSE transport runs SSE, not streamable-http."""
        with patch("unifi_mcp_shared.transport.os.getpid", return_value=1):
            await run_transports(
                server=mock_server,
                http_enabled=True,
                host="0.0.0.0",
                port=3000,
                http_transport="sse",
                logger=logging.getLogger("test"),
            )
        mock_server.run_sse_async.assert_awaited_once()
        mock_server.run_streamable_http_async.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_non_pid1_runs_both_transports(self, mock_server):
        """When not PID 1 (local dev with force), both transports start."""
        # Make both return immediately to avoid hanging
        mock_server.run_stdio_async.return_value = None
        mock_server.run_streamable_http_async.return_value = None

        with patch("unifi_mcp_shared.transport.os.getpid", return_value=12345):
            await run_transports(
                server=mock_server,
                http_enabled=True,
                host="0.0.0.0",
                port=3000,
                http_transport="streamable-http",
                logger=logging.getLogger("test"),
            )
        mock_server.run_stdio_async.assert_awaited_once()
        mock_server.run_streamable_http_async.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_pid1_http_error_logged_not_raised(self, mock_server, caplog):
        """HTTP errors are logged but don't crash in PID 1 mode (matches dual-transport behaviour)."""
        mock_server.run_streamable_http_async.side_effect = RuntimeError("bind failed")

        with patch("unifi_mcp_shared.transport.os.getpid", return_value=1):
            # Should not raise — run_http catches the exception internally
            await run_transports(
                server=mock_server,
                http_enabled=True,
                host="0.0.0.0",
                port=3000,
                http_transport="streamable-http",
                logger=logging.getLogger("test"),
            )
        assert "bind failed" in caplog.text
