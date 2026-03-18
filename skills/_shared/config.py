"""MCP server URL discovery for skill scripts.

Reads server URLs from environment variables with localhost fallbacks.
Each MCP server binds to a distinct port when HTTP is enabled.
"""
import os

DEFAULT_PORTS = {
    "network": 3000,
    "protect": 3001,
    "access": 3002,
}

ENV_VARS = {
    "network": "UNIFI_NETWORK_MCP_URL",
    "protect": "UNIFI_PROTECT_MCP_URL",
    "access": "UNIFI_ACCESS_MCP_URL",
}


def get_server_url(server: str) -> str:
    """Get the HTTP URL for an MCP server."""
    if server not in ENV_VARS:
        raise ValueError(f"Unknown server: {server}. Valid: {list(ENV_VARS.keys())}")
    env_val = os.environ.get(ENV_VARS[server])
    if env_val:
        return env_val
    return f"http://localhost:{DEFAULT_PORTS[server]}"


def get_all_server_urls() -> dict[str, str]:
    """Get URLs for all known MCP servers."""
    return {name: get_server_url(name) for name in ENV_VARS}
