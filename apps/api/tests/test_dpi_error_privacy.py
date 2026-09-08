"""DPI controller failures must be safe beyond the MCP tool surface."""

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiounifi.errors import LoginRequired
from httpx import ASGITransport, AsyncClient
from unifi_core.network.managers.connection_manager import ConnectionManager
from unifi_core.network.managers.stats_manager import StatsManager

from tests.test_action_endpoint import _bootstrap


@pytest.mark.asyncio
@pytest.mark.parametrize("surface", ["rest", "graphql"])
@pytest.mark.parametrize("handler", ["dpi_apps", "dpi_groups"])
async def test_dpi_failure_omits_controller_text(surface, handler, tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("UNIFI_API_DB_KEY", "k")
    app, key, cid = await _bootstrap(tmp_path, scopes="read")
    private = "controller-only-dpi-api-token-508d"
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
    factory = MagicMock()
    factory.get_domain_manager = AsyncMock(return_value=manager)
    app.state.manager_factory = factory
    caplog.set_level(logging.DEBUG)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        headers = {"Authorization": f"Bearer {key}"}
        if surface == "rest":
            response = await client.get(f"/v1/sites/default/stats/dpi?controller={cid}", headers=headers)
            assert response.status_code == 500
        else:
            query = '{ network { dpiStats(controller: "' + cid + '") { applications categories } } }'
            response = await client.post("/v1/graphql", headers=headers, json={"query": query})
            assert response.status_code == 200
            assert response.json()["errors"]
            assert "DPI stats refresh failed" in response.text

    assert failed_update.await_count == 2
    assert connection.reconnect_blocked
    assert private not in response.text
    assert private not in caplog.text
    await connection.cleanup()
