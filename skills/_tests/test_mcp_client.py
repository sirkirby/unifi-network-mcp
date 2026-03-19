"""Tests for MCP HTTP client (stdlib-based, synchronous)."""
import io
import json
import urllib.error
from unittest.mock import patch, MagicMock

import pytest

from skills._shared.mcp_client import MCPClient, MCPConnectionError, MCPToolError


def _mock_response(data: dict, status: int = 200) -> MagicMock:
    """Create a mock urllib response with JSON body."""
    raw = json.dumps(data).encode("utf-8")
    resp = MagicMock()
    resp.read.return_value = raw
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_client_init():
    client = MCPClient("http://localhost:3000")
    assert client.base_url == "http://localhost:3000"


def test_call_tool_success():
    """Test successful tool call via MCP HTTP."""
    tool_result = {"success": True, "data": [{"name": "AP-LR"}]}
    mock_resp = _mock_response({
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"content": [{"type": "text", "text": json.dumps(tool_result)}]},
    })
    client = MCPClient("http://localhost:3000")
    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = client.call_tool("unifi_list_devices", {})
        assert result["success"] is True
        assert result["data"][0]["name"] == "AP-LR"


def test_call_tool_connection_error():
    """Test connection error raises MCPConnectionError."""
    client = MCPClient("http://localhost:9999")
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
        with pytest.raises(MCPConnectionError, match="Cannot connect"):
            client.call_tool("unifi_list_devices", {})


def test_call_tools_parallel():
    """Test parallel tool calls."""
    tool_result = {"success": True, "data": "ok"}
    mock_resp = _mock_response({
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"content": [{"type": "text", "text": json.dumps(tool_result)}]},
    })
    client = MCPClient("http://localhost:3000")
    with patch("urllib.request.urlopen", return_value=mock_resp):
        results = client.call_tools_parallel([
            ("unifi_get_system_info", {}),
            ("unifi_list_devices", {}),
        ])
        assert len(results) == 2
        assert all(r["success"] for r in results)


def test_check_server_ready_success():
    """Test server readiness check."""
    tool_result = {"success": True, "data": {"tools": []}}
    mock_resp = _mock_response({
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"content": [{"type": "text", "text": json.dumps(tool_result)}]},
    })
    client = MCPClient("http://localhost:3000")
    with patch("urllib.request.urlopen", return_value=mock_resp):
        ready = client.check_ready("unifi_tool_index")
        assert ready is True


def test_check_server_ready_failure():
    """Test readiness check returns False when server unreachable."""
    client = MCPClient("http://localhost:9999")
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
        ready = client.check_ready("unifi_tool_index")
        assert ready is False


def test_setup_required_error():
    """Test setup_required JSON output when server unreachable."""
    client = MCPClient("http://localhost:9999")
    error = client.get_setup_error()
    assert error["success"] is False
    assert error["error"] == "setup_required"
    assert "9999" in error["message"]


def test_jsonrpc_error_raises_tool_error():
    """Test JSON-RPC error response raises MCPToolError."""
    mock_resp = _mock_response({
        "jsonrpc": "2.0",
        "id": 1,
        "error": {"code": -32601, "message": "Tool not found"},
    })
    client = MCPClient("http://localhost:3000")
    with patch("urllib.request.urlopen", return_value=mock_resp):
        with pytest.raises(MCPToolError, match="Tool not found"):
            client.call_tool("nonexistent_tool", {})
