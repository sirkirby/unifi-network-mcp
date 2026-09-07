"""Tool error logging must not reintroduce private controller identifiers."""

import importlib
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize("domain", ["clients", "devices"])
async def test_detail_error_logs_do_not_include_private_exception(domain, monkeypatch, caplog):
    monkeypatch.setenv("UNIFI_HOST", "127.0.0.1")
    monkeypatch.setenv("UNIFI_USERNAME", "test")
    monkeypatch.setenv("UNIFI_PASSWORD", "test")
    from unifi_network_mcp import runtime

    singular = "client" if domain == "clients" else "device"
    private = "aa:bb:cc:11:22:33 private-owner password=do-not-log"
    manager = MagicMock()
    method = f"get_{singular}_details"
    setattr(manager, method, AsyncMock(side_effect=RuntimeError(private)))
    monkeypatch.setattr(runtime, f"{singular}_manager", manager)
    module = importlib.import_module(f"unifi_network_mcp.tools.{domain}")
    monkeypatch.setattr(module, f"{singular}_manager", manager)
    with caplog.at_level(logging.ERROR, logger=module.__name__):
        result = await getattr(module, method)("aa:bb:cc:11:22:33")
    assert result["success"] is False
    records = [record for record in caplog.records if record.name == module.__name__]
    assert records
    for record in records:
        assert record.exc_info is None
        for marker in ("aa:bb:cc:11:22:33", "private-owner", "do-not-log"):
            assert marker not in record.getMessage()
            assert marker not in repr(record.args)
    assert "RuntimeError" in caplog.text


def _assert_no_private_failure(caplog, result, private, error_class):
    assert result["success"] is False
    assert private not in repr(result)
    assert private not in caplog.text
    assert caplog.records
    for record in caplog.records:
        assert record.exc_info is None
        assert private not in repr(record.args)
    assert error_class in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["read", "preview", "update_fetch", "update_put"])
@pytest.mark.parametrize("error_kind", ["opaque", "request", "response"])
async def test_autobackup_tool_manager_chain_omits_private_errors(phase, error_kind, monkeypatch, caplog):
    from aiounifi.errors import RequestError, ResponseError

    from unifi_core.network.managers.connection_manager import ConnectionManager
    from unifi_core.network.managers.system_manager import SystemManager
    from unifi_network_mcp import runtime

    private = "controller-only-autobackup-token-719c"

    class OpaqueError(Exception):
        def __str__(self):
            return private

    error = {"opaque": OpaqueError, "request": RequestError, "response": ResponseError}[error_kind](private)
    connection = ConnectionManager("127.0.0.1", "test", "test")
    controller = MagicMock()
    controller.connectivity.config.session = SimpleNamespace(closed=False, close=AsyncMock())
    controller.request = AsyncMock(side_effect=error)
    if phase == "update_put":
        controller.request.side_effect = [{"data": [{"_id": "settings-1"}]}, error]
    connection.controller = controller
    connection._aiohttp_session = controller.connectivity.config.session
    connection._initialized = True
    manager = SystemManager(connection)
    monkeypatch.setattr(runtime, "system_manager", manager)
    module = importlib.import_module("unifi_network_mcp.tools.system")
    monkeypatch.setattr(module, "system_manager", manager)

    with caplog.at_level(logging.ERROR):
        if phase == "read":
            result = await module.get_autobackup_settings()
        else:
            result = await module.update_autobackup_settings({"autobackup_enabled": True}, confirm=phase != "preview")

    _assert_no_private_failure(caplog, result, private, type(error).__name__)
    assert controller.request.await_count == (2 if phase == "update_put" else 1)
    await connection.cleanup()


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["initialize", "reauthenticate"])
async def test_followup_tool_call_omits_cached_authentication_failure(phase, monkeypatch, caplog):
    from aiounifi.errors import LoginRequired, Unauthorized

    from unifi_core.network.managers import connection_manager as cm_module
    from unifi_core.network.managers.system_manager import SystemManager
    from unifi_network_mcp import runtime

    private = "controller-only-auth-token-583a"

    def fail_connector(**kwargs):
        raise LoginRequired(private)

    monkeypatch.setattr(cm_module.aiohttp, "TCPConnector", fail_connector)
    connection = cm_module.ConnectionManager("127.0.0.1", "test", "test")
    if phase == "reauthenticate":
        controller = MagicMock()
        controller.connectivity.config.session = SimpleNamespace(closed=False, close=AsyncMock())
        controller.request = AsyncMock(side_effect=LoginRequired(private))
        controller.login = AsyncMock(side_effect=Unauthorized(private))
        connection.controller = controller
        connection._aiohttp_session = controller.connectivity.config.session
        connection._initialized = True
    manager = SystemManager(connection)
    monkeypatch.setattr(runtime, "system_manager", manager)
    module = importlib.import_module("unifi_network_mcp.tools.system")
    monkeypatch.setattr(module, "system_manager", manager)

    with caplog.at_level(logging.ERROR):
        if phase == "initialize":
            assert await connection.initialize() is False
        result = await module.get_system_info()
        followup = await module.get_system_info()

    assert result["success"] is False
    assert private not in repr(result)
    assert private not in repr(followup)
    assert private not in caplog.text
    assert private not in connection.last_connection_error
    assert connection.reconnect_blocked
    await connection.cleanup()


@pytest.mark.asyncio
@pytest.mark.parametrize("handler", ["dpi_apps", "dpi_groups"])
async def test_dpi_tool_manager_refresh_chain_omits_retry_error(handler, monkeypatch, caplog):
    from aiounifi.errors import LoginRequired

    from unifi_core.network.managers.connection_manager import ConnectionManager
    from unifi_core.network.managers.stats_manager import StatsManager
    from unifi_network_mcp import runtime

    private = "controller-only-dpi-token-937b"
    connection = ConnectionManager("127.0.0.1", "test", "test")
    controller = MagicMock()
    controller.connectivity.config.session = SimpleNamespace(closed=False, close=AsyncMock())
    controller.login = AsyncMock()
    controller.dpi_apps.update = AsyncMock()
    controller.dpi_groups.update = AsyncMock()
    failed_update = AsyncMock(side_effect=LoginRequired(private))
    getattr(controller, handler).update = failed_update
    connection.controller = controller
    connection._aiohttp_session = controller.connectivity.config.session
    connection._initialized = True
    manager = StatsManager(connection, MagicMock())
    monkeypatch.setattr(runtime, "stats_manager", manager)
    module = importlib.import_module("unifi_network_mcp.tools.stats")
    monkeypatch.setattr(module, "stats_manager", manager)

    with caplog.at_level(logging.ERROR):
        result = await module.get_dpi_stats()

    _assert_no_private_failure(caplog, result, private, "LoginRequired")
    assert failed_update.await_count == 2
    controller.login.assert_awaited_once()
    assert connection.reconnect_blocked
    await connection.cleanup()
