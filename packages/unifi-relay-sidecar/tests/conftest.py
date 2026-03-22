"""Shared fixtures for unifi-relay-sidecar tests."""

import pytest

from unifi_relay_sidecar.config import RelayConfig
from unifi_relay_sidecar.protocol import ToolInfo


@pytest.fixture
def sample_tools():
    return [
        ToolInfo(
            name="unifi_list_devices",
            description="List all UniFi network devices",
            input_schema={"type": "object", "properties": {"compact": {"type": "boolean"}}},
            annotations={"readOnlyHint": True, "openWorldHint": False},
            server_origin="unifi-network-mcp",
        ),
        ToolInfo(
            name="unifi_reboot_device",
            description="Reboot a device",
            input_schema={"type": "object", "properties": {"mac": {"type": "string"}}, "required": ["mac"]},
            annotations={"readOnlyHint": False, "destructiveHint": True},
            server_origin="unifi-network-mcp",
        ),
    ]
