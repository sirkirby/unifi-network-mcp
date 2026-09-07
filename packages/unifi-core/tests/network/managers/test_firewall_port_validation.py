"""Port and selector validation at the Core firewall create boundary.

This is the one create path both the MCP tool and the API dispatcher execute
through, so a check that only lives in a tool wrapper is not enough."""

import copy
from unittest.mock import AsyncMock, MagicMock

import pytest
from unifi_core.network.managers.firewall_manager import FirewallManager


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", ["source", "destination"])
@pytest.mark.parametrize(
    "endpoint",
    [
        {"ports": ["445"]},
        {"port_matching_type": "SPECIFIC"},
        {"port_matching_type": "SPECIFIC", "port": 445},
        {"port_matching_type": "SPECIFIC", "port": ["445"]},
        {"port_matching_type": "SPECIFIC", "port": ""},
        {"port_matching_type": "SPECIFIC", "port": " "},
    ],
)
async def test_invalid_ports_fail_before_controller_connection(direction, endpoint):
    connection = MagicMock()
    connection.ensure_connected = AsyncMock()
    connection.request = AsyncMock()
    manager = FirewallManager(connection)

    with pytest.raises(ValueError, match=rf"{direction}\.port"):
        await manager.create_firewall_policy({direction: endpoint})

    connection.ensure_connected.assert_not_awaited()
    connection.request.assert_not_awaited()


@pytest.mark.asyncio
async def test_valid_ports_reach_controller_without_mutating_input():
    data = {
        "name": "Specific ports",
        "action": "ALLOW",
        "enabled": False,
        "source": {"port_matching_type": "SPECIFIC", "port": "445"},
        "destination": {"port_matching_type": "SPECIFIC", "port": "8443"},
    }
    before = copy.deepcopy(data)
    connection = MagicMock()
    connection.ensure_connected = AsyncMock(return_value=True)
    connection.request = AsyncMock(return_value={"_id": "created-policy", **data})

    created = await FirewallManager(connection).create_firewall_policy(data)

    connection.request.assert_awaited_once()
    assert connection.request.call_args.args[0].data == before
    assert created.raw["source"]["port"] == "445"
    assert created.raw["destination"]["port"] == "8443"
    assert data == before


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", ["source", "destination"])
@pytest.mark.parametrize(
    ("endpoint", "expected"),
    [
        ({"matching_target": "CLIENT"}, "client_macs"),
        ({"matching_target": "CLIENT", "client_macs": []}, "client_macs"),
        ({"matching_target": "CLIENT", "client_macs": ["nope"]}, "client_macs"),
        ({"port_matching_type": "OBJECT"}, "port_group_id"),
        ({"port_matching_type": "ANY", "port": "53"}, "port_matching_type"),
        ({"matching_target": "ANY", "client_macs": ["aa:bb:cc:dd:ee:ff"]}, "matching_target"),
        ({"port_group_id": "g1"}, "port_matching_type"),
    ],
)
async def test_inactive_selectors_fail_before_controller_connection(direction, endpoint, expected):
    """The controller accepts a selector under the wrong enum and silently ignores it."""
    connection = MagicMock()
    connection.ensure_connected = AsyncMock()
    connection.request = AsyncMock()
    manager = FirewallManager(connection)

    with pytest.raises(ValueError, match=expected):
        await manager.create_firewall_policy({direction: endpoint})

    connection.ensure_connected.assert_not_awaited()
    connection.request.assert_not_awaited()


@pytest.mark.asyncio
async def test_activated_selectors_reach_the_controller():
    data = {
        "name": "Client and port group",
        "action": "BLOCK",
        "enabled": False,
        "source": {"matching_target": "CLIENT", "client_macs": ["AA:BB:CC:DD:EE:FF"]},
        "destination": {"port_matching_type": "OBJECT", "port_group_id": "grp-1"},
    }
    connection = MagicMock()
    connection.ensure_connected = AsyncMock(return_value=True)
    connection.request = AsyncMock(return_value={"_id": "created-policy", **data})

    await FirewallManager(connection).create_firewall_policy(data)

    sent = connection.request.call_args.args[0].data
    assert sent["source"]["client_macs"] == ["aa:bb:cc:dd:ee:ff"]
    assert sent["destination"]["port_group_id"] == "grp-1"
