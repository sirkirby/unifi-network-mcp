"""Tests for RelaySidecar orchestrator."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from unifi_mcp_relay.main import RelaySidecar, _TIMELINE_TOOL
from unifi_mcp_relay.config import RelayConfig
from unifi_mcp_relay.location_timeline import TOOL_NAME


@pytest.fixture
def config():
    return RelayConfig(
        relay_url="https://my-worker.workers.dev",
        relay_token="test-token",
        location_name="Test Lab",
        servers=["http://localhost:3000"],
        refresh_interval=60,
    )


@pytest.mark.asyncio
async def test_sidecar_discovers_and_builds_catalog(config):
    sidecar = RelaySidecar(config)
    from unifi_mcp_relay.discovery import ServerInfo
    from unifi_mcp_relay.protocol import ToolInfo

    mock_info = ServerInfo(
        name="unifi-network-mcp",
        url="http://localhost:3000",
        tools=[ToolInfo(name="unifi_list_devices", description="List", server_origin="unifi-network-mcp")],
    )

    with patch("unifi_mcp_relay.main.discover_all", new_callable=AsyncMock) as mock_discover:
        mock_discover.return_value = [mock_info]
        with patch("unifi_mcp_relay.main.ToolForwarder") as MockFwd:
            mock_fwd_instance = AsyncMock()
            MockFwd.return_value = mock_fwd_instance

            catalog = await sidecar._discover_catalog()
            # 1 discovered + 1 relay-native (unifi_location_timeline)
            assert len(catalog) == 2
            assert catalog[0].name == "unifi_list_devices"
            assert catalog[1].name == TOOL_NAME
            mock_fwd_instance.open.assert_called_once()


@pytest.mark.asyncio
async def test_sidecar_catalog_includes_relay_native_tool(config):
    """The relay-native timeline tool appears in the catalog with correct metadata."""
    sidecar = RelaySidecar(config)
    from unifi_mcp_relay.discovery import ServerInfo

    mock_info = ServerInfo(name="test", url="http://localhost:3000", tools=[])

    with patch("unifi_mcp_relay.main.discover_all", new_callable=AsyncMock) as mock_discover:
        mock_discover.return_value = [mock_info]
        with patch("unifi_mcp_relay.main.ToolForwarder") as MockFwd:
            MockFwd.return_value = AsyncMock()
            catalog = await sidecar._discover_catalog()

    timeline_tools = [t for t in catalog if t.name == TOOL_NAME]
    assert len(timeline_tools) == 1
    tool = timeline_tools[0]
    assert tool.server_origin == "unifi-mcp-relay"
    assert tool.annotations["readOnlyHint"] is True
    assert tool.input_schema is not None
    assert "start_time" in tool.input_schema["properties"]


@pytest.mark.asyncio
async def test_sidecar_tool_call_handler_delegates_to_forwarder(config):
    sidecar = RelaySidecar(config)
    from unifi_mcp_relay.discovery import ServerInfo
    from unifi_mcp_relay.protocol import ToolInfo

    mock_info = ServerInfo(
        name="unifi-network-mcp",
        url="http://localhost:3000",
        tools=[ToolInfo(name="unifi_list_devices", description="List", server_origin="unifi-network-mcp")],
    )

    with patch("unifi_mcp_relay.main.discover_all", new_callable=AsyncMock) as mock_discover:
        mock_discover.return_value = [mock_info]
        with patch("unifi_mcp_relay.main.ToolForwarder") as MockFwd:
            mock_fwd_instance = AsyncMock()
            MockFwd.return_value = mock_fwd_instance
            await sidecar._discover_catalog()

    mock_fwd_instance.forward_with_error = AsyncMock(return_value={"success": True, "data": []})
    sidecar._forwarder = mock_fwd_instance

    result, error = await sidecar._handle_tool_call("unifi_list_devices", {})
    assert result == {"success": True, "data": []}
    assert error is None


@pytest.mark.asyncio
async def test_sidecar_tool_call_handler_returns_error_string(config):
    sidecar = RelaySidecar(config)
    from unifi_mcp_relay.forwarder import ToolForwarder

    mock_fwd = AsyncMock(spec=ToolForwarder)
    mock_fwd.forward_with_error = AsyncMock(return_value="Connection refused")
    sidecar._forwarder = mock_fwd

    result, error = await sidecar._handle_tool_call("unifi_list_devices", {})
    assert result is None
    assert error == "Connection refused"


@pytest.mark.asyncio
async def test_sidecar_routes_timeline_to_handler(config):
    """unifi_location_timeline calls are handled locally, not forwarded."""
    sidecar = RelaySidecar(config)
    sidecar._client._location_id = "loc_abc"

    mock_fwd = AsyncMock()
    # Simulate network events returned by forwarder.forward()
    mock_fwd.forward = AsyncMock(return_value={
        "success": True,
        "data": [
            {"timestamp": "2026-03-24T10:00:00+00:00", "type": "client_connect", "msg": "Client connected"},
        ],
    })
    sidecar._forwarder = mock_fwd

    result, error = await sidecar._handle_tool_call(
        TOOL_NAME,
        {"start_time": "2026-03-24T00:00:00Z", "end_time": "2026-03-24T23:59:59Z", "products": ["network"]},
    )
    assert error is None
    assert result["success"] is True
    assert "timeline" in result["data"]
    # forward should have been called (not forward_with_error)
    mock_fwd.forward.assert_called()
    mock_fwd.forward_with_error.assert_not_called()


@pytest.mark.asyncio
async def test_sidecar_timeline_validation_error_returns_error(config):
    """Invalid timeline input returns an error through the handler."""
    sidecar = RelaySidecar(config)
    sidecar._client._location_id = "loc_abc"
    sidecar._forwarder = AsyncMock()

    result, error = await sidecar._handle_tool_call(
        TOOL_NAME,
        {"start_time": "", "end_time": "2026-03-24T23:59:59Z"},
    )
    assert result is None
    assert error is not None
    assert "start_time" in error


@pytest.mark.asyncio
async def test_sidecar_timeline_handler_exception_returns_error(config):
    """If the timeline handler raises, the sidecar returns an error string."""
    sidecar = RelaySidecar(config)
    sidecar._client._location_id = "loc_abc"

    mock_fwd = AsyncMock()
    sidecar._forwarder = mock_fwd

    with patch("unifi_mcp_relay.main.handle_location_timeline", new_callable=AsyncMock) as mock_handler:
        mock_handler.side_effect = RuntimeError("boom")
        result, error = await sidecar._handle_tool_call(
            TOOL_NAME,
            {"start_time": "2026-03-24T00:00:00Z", "end_time": "2026-03-24T23:59:59Z"},
        )
    assert result is None
    assert "boom" in error
