"""Tests for MCP HTTP client."""
import json
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from skills._shared.mcp_client import MCPClient, MCPConnectionError, MCPToolError


@pytest.mark.asyncio
async def test_client_init():
    client = MCPClient("http://localhost:3000")
    assert client.base_url == "http://localhost:3000"
    await client.close()


@pytest.mark.asyncio
async def test_call_tool_success():
    """Test successful tool call via MCP HTTP."""
    tool_result = {"success": True, "data": [{"name": "AP-LR"}]}
    mock_response = httpx.Response(
        200,
        json={"jsonrpc": "2.0", "id": 1, "result": {
            "content": [{"type": "text", "text": json.dumps(tool_result)}]
        }},
        request=httpx.Request("POST", "http://localhost:3000/mcp"),
    )
    client = MCPClient("http://localhost:3000")
    with patch.object(client._http, "post", new_callable=AsyncMock, return_value=mock_response):
        result = await client.call_tool("unifi_list_devices", {})
        assert result["success"] is True
        assert result["data"][0]["name"] == "AP-LR"
    await client.close()


@pytest.mark.asyncio
async def test_call_tool_connection_error():
    """Test connection error raises MCPConnectionError."""
    client = MCPClient("http://localhost:9999")
    with patch.object(client._http, "post", new_callable=AsyncMock, side_effect=httpx.ConnectError("refused")):
        with pytest.raises(MCPConnectionError, match="Cannot connect"):
            await client.call_tool("unifi_list_devices", {})
    await client.close()


@pytest.mark.asyncio
async def test_call_tools_parallel():
    """Test parallel tool calls."""
    tool_result = {"success": True, "data": "ok"}
    mock_response = httpx.Response(
        200,
        json={"jsonrpc": "2.0", "id": 1, "result": {
            "content": [{"type": "text", "text": json.dumps(tool_result)}]
        }},
        request=httpx.Request("POST", "http://localhost:3000/mcp"),
    )
    client = MCPClient("http://localhost:3000")
    with patch.object(client._http, "post", new_callable=AsyncMock, return_value=mock_response):
        results = await client.call_tools_parallel([
            ("unifi_get_system_info", {}),
            ("unifi_list_devices", {}),
        ])
        assert len(results) == 2
        assert all(r["success"] for r in results)
    await client.close()


@pytest.mark.asyncio
async def test_check_server_ready_success():
    """Test server readiness check."""
    tool_result = {"success": True, "data": {"tools": []}}
    mock_response = httpx.Response(
        200,
        json={"jsonrpc": "2.0", "id": 1, "result": {
            "content": [{"type": "text", "text": json.dumps(tool_result)}]
        }},
        request=httpx.Request("POST", "http://localhost:3000/mcp"),
    )
    client = MCPClient("http://localhost:3000")
    with patch.object(client._http, "post", new_callable=AsyncMock, return_value=mock_response):
        ready = await client.check_ready("unifi_tool_index")
        assert ready is True
    await client.close()


@pytest.mark.asyncio
async def test_check_server_ready_failure():
    """Test readiness check returns False when server unreachable."""
    client = MCPClient("http://localhost:9999")
    with patch.object(client._http, "post", new_callable=AsyncMock, side_effect=httpx.ConnectError("refused")):
        ready = await client.check_ready("unifi_tool_index")
        assert ready is False
    await client.close()


@pytest.mark.asyncio
async def test_setup_required_error():
    """Test setup_required JSON output when server unreachable."""
    client = MCPClient("http://localhost:9999")
    error = await client.get_setup_error()
    assert error["success"] is False
    assert error["error"] == "setup_required"
    assert "9999" in error["message"]
    await client.close()


@pytest.mark.asyncio
async def test_jsonrpc_error_raises_tool_error():
    """Test JSON-RPC error response raises MCPToolError."""
    mock_response = httpx.Response(
        200,
        json={"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "Tool not found"}},
        request=httpx.Request("POST", "http://localhost:3000/mcp"),
    )
    client = MCPClient("http://localhost:3000")
    with patch.object(client._http, "post", new_callable=AsyncMock, return_value=mock_response):
        with pytest.raises(MCPToolError, match="Tool not found"):
            await client.call_tool("nonexistent_tool", {})
    await client.close()
