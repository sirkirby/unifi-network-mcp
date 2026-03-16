"""Tests for dual auth integration into the network server."""

import os

from unifi_core.auth import AuthMethod, UniFiAuth


def test_api_key_from_env(monkeypatch):
    monkeypatch.setenv("UNIFI_API_KEY", "test-key-123")
    auth = UniFiAuth(api_key=os.environ.get("UNIFI_API_KEY"))
    assert auth.has_api_key is True


def test_no_api_key_configured():
    auth = UniFiAuth()
    assert auth.has_api_key is False


def test_empty_api_key_not_configured():
    auth = UniFiAuth(api_key="")
    assert auth.has_api_key is False


def test_auth_method_default_is_local_only():
    method = AuthMethod.from_string(None)
    assert method == AuthMethod.LOCAL_ONLY


def test_auth_method_from_valid_string():
    assert AuthMethod.from_string("api_key_only") == AuthMethod.API_KEY_ONLY
    assert AuthMethod.from_string("either") == AuthMethod.EITHER
    assert AuthMethod.from_string("local_only") == AuthMethod.LOCAL_ONLY


def test_auth_method_invalid_falls_back():
    assert AuthMethod.from_string("invalid") == AuthMethod.LOCAL_ONLY


def test_tool_metadata_auth_method_default():
    """ToolMetadata defaults auth_method to local_only."""
    from unifi_network_mcp.tool_index import ToolMetadata

    meta = ToolMetadata(name="test_tool", description="A test tool")
    assert meta.auth_method == "local_only"


def test_tool_metadata_auth_method_custom():
    """ToolMetadata accepts a custom auth_method."""
    from unifi_network_mcp.tool_index import ToolMetadata

    meta = ToolMetadata(name="test_tool", description="A test tool", auth_method="api_key_only")
    assert meta.auth_method == "api_key_only"


def test_register_tool_with_auth_method():
    """register_tool stores auth_method in the registry."""
    from unifi_network_mcp.tool_index import TOOL_REGISTRY, register_tool

    register_tool(
        name="_test_auth_tool",
        description="test",
        auth_method="either",
    )
    assert TOOL_REGISTRY["_test_auth_tool"].auth_method == "either"

    # Cleanup
    del TOOL_REGISTRY["_test_auth_tool"]


def test_register_tool_default_auth_method():
    """register_tool defaults auth_method to local_only."""
    from unifi_network_mcp.tool_index import TOOL_REGISTRY, register_tool

    register_tool(
        name="_test_auth_default_tool",
        description="test",
    )
    assert TOOL_REGISTRY["_test_auth_default_tool"].auth_method == "local_only"

    # Cleanup
    del TOOL_REGISTRY["_test_auth_default_tool"]
