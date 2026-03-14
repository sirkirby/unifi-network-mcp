"""Tests for firewall manager update_traffic_route mutation safety.

Verifies that update_traffic_route() uses deepcopy to protect cached
TrafficRoute.raw from mutation — the same pattern tested in
test_device_radio.py for device radio updates.
"""

import copy
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("UNIFI_HOST", "127.0.0.1")
os.environ.setdefault("UNIFI_USERNAME", "test")
os.environ.setdefault("UNIFI_PASSWORD", "test")

SAMPLE_ROUTE_RAW = {
    "_id": "route001",
    "enabled": True,
    "description": "Test route",
    "network_id": "net001",
    "interface": "WAN",
    "kill_switch_enabled": False,
    "domains": [
        {"domain": "example.com", "ports": [443, 80]},
        {"domain": "other.com", "ports": [8443]},
    ],
}


def _make_traffic_route(raw: dict | None = None):
    """Create a mock TrafficRoute with the given raw dict."""
    route = MagicMock()
    route.raw = raw if raw is not None else copy.deepcopy(SAMPLE_ROUTE_RAW)
    route.id = route.raw["_id"]
    route.enabled = route.raw.get("enabled", True)
    return route


def _make_mock_connection(routes: list | None = None):
    """Create a mock ConnectionManager pre-wired with get_traffic_routes results."""
    conn = MagicMock()
    conn.ensure_connected = AsyncMock(return_value=True)
    conn.request = AsyncMock(return_value={})
    conn.site = "default"
    conn.get_cached = MagicMock(return_value=None)
    conn._update_cache = MagicMock()
    conn._invalidate_cache = MagicMock()
    return conn


@pytest.fixture
def mock_connection():
    return _make_mock_connection()


@pytest.fixture
def firewall_manager(mock_connection):
    from src.managers.firewall_manager import FirewallManager

    return FirewallManager(mock_connection)


class TestUpdateTrafficRouteMutationSafety:
    """Ensure update_traffic_route does not mutate the cached TrafficRoute.raw."""

    @pytest.mark.asyncio
    async def test_does_not_mutate_cached_route(self, firewall_manager, mock_connection):
        """The cached TrafficRoute.raw must be unchanged after update_traffic_route."""
        route = _make_traffic_route()
        original_raw = copy.deepcopy(route.raw)

        with patch.object(firewall_manager, "get_traffic_routes", new_callable=AsyncMock, return_value=[route]):
            await firewall_manager.update_traffic_route("route001", {"description": "Changed", "enabled": False})

        assert route.raw == original_raw

    @pytest.mark.asyncio
    async def test_happy_path_sends_merged_payload(self, firewall_manager, mock_connection):
        """The API request should contain original fields merged with updates."""
        route = _make_traffic_route()
        updates = {"description": "Updated route", "kill_switch_enabled": True}

        with patch.object(firewall_manager, "get_traffic_routes", new_callable=AsyncMock, return_value=[route]):
            result = await firewall_manager.update_traffic_route("route001", updates)

        assert result is True
        mock_connection.request.assert_called_once()

        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        payload = api_request.data

        # Original fields preserved
        assert payload["_id"] == "route001"
        assert payload["network_id"] == "net001"
        assert payload["interface"] == "WAN"
        # Updates applied
        assert payload["description"] == "Updated route"
        assert payload["kill_switch_enabled"] is True

    @pytest.mark.asyncio
    async def test_does_not_mutate_cached_route_on_api_failure(self, firewall_manager, mock_connection):
        """Even when the API call fails, the cached TrafficRoute.raw must be untouched."""
        route = _make_traffic_route()
        original_raw = copy.deepcopy(route.raw)

        mock_connection.request = AsyncMock(side_effect=Exception("API error"))

        with patch.object(firewall_manager, "get_traffic_routes", new_callable=AsyncMock, return_value=[route]):
            result = await firewall_manager.update_traffic_route("route001", {"description": "Should not persist"})

        assert result is False
        assert route.raw == original_raw
