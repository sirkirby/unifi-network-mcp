"""Unit tests for static routing functionality.

Tests the RoutingManager methods for managing static routes.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.managers.routing_manager import RoutingManager


class TestRoutingManagerGetRoutes:
    """Test suite for RoutingManager.get_routes method."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mock ConnectionManager."""
        mock = MagicMock()
        mock.ensure_connected = AsyncMock(return_value=True)
        mock.controller = MagicMock()
        mock.site = "default"
        mock.request = AsyncMock(return_value=[])
        mock._invalidate_cache = MagicMock()
        mock.get_cached = MagicMock(return_value=None)
        mock._update_cache = MagicMock()
        return mock

    @pytest.fixture
    def routing_manager(self, mock_connection_manager):
        """Create a RoutingManager with mocked connection."""
        return RoutingManager(mock_connection_manager)

    @pytest.fixture
    def sample_routes(self):
        """Sample static route data returned by the API."""
        return [
            {
                "_id": "route_id_1",
                "name": "VPN Network",
                "static-route_network": "10.0.0.0/8",
                "static-route_nexthop": "192.168.1.1",
                "static-route_distance": 1,
                "enabled": True,
                "type": "nexthop-route",
                "site_id": "site123",
            },
            {
                "_id": "route_id_2",
                "name": "Office Network",
                "static-route_network": "172.16.0.0/12",
                "static-route_nexthop": "192.168.1.254",
                "static-route_distance": 10,
                "enabled": False,
                "type": "nexthop-route",
                "site_id": "site123",
            },
        ]

    @pytest.mark.asyncio
    async def test_get_routes_success(self, routing_manager, sample_routes):
        """Test successfully getting static routes."""
        routing_manager._connection.request = AsyncMock(return_value=sample_routes)

        result = await routing_manager.get_routes()

        assert len(result) == 2
        assert result[0]["name"] == "VPN Network"
        assert result[1]["name"] == "Office Network"
        routing_manager._connection._update_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_routes_from_cache(self, routing_manager, sample_routes):
        """Test getting static routes from cache."""
        routing_manager._connection.get_cached = MagicMock(return_value=sample_routes)

        result = await routing_manager.get_routes()

        assert len(result) == 2
        routing_manager._connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_routes_empty(self, routing_manager):
        """Test getting static routes when none exist."""
        routing_manager._connection.request = AsyncMock(return_value=[])

        result = await routing_manager.get_routes()

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_routes_api_error(self, routing_manager):
        """Test handling API errors gracefully."""
        routing_manager._connection.request = AsyncMock(
            side_effect=Exception("API Error")
        )

        result = await routing_manager.get_routes()

        assert result == []


class TestRoutingManagerCreateRoute:
    """Test suite for RoutingManager.create_route method."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mock ConnectionManager."""
        mock = MagicMock()
        mock.ensure_connected = AsyncMock(return_value=True)
        mock.controller = MagicMock()
        mock.site = "default"
        mock.request = AsyncMock(return_value=None)
        mock._invalidate_cache = MagicMock()
        mock.get_cached = MagicMock(return_value=None)
        mock._update_cache = MagicMock()
        return mock

    @pytest.fixture
    def routing_manager(self, mock_connection_manager):
        """Create a RoutingManager with mocked connection."""
        return RoutingManager(mock_connection_manager)

    @pytest.mark.asyncio
    async def test_create_route_success(self, routing_manager):
        """Test successfully creating a static route."""
        created_route = {
            "_id": "new_route_id",
            "name": "Test Route",
            "static-route_network": "10.10.0.0/16",
            "static-route_nexthop": "192.168.1.1",
            "static-route_distance": 5,
            "enabled": True,
        }
        routing_manager._connection.request = AsyncMock(return_value=[created_route])

        result = await routing_manager.create_route(
            name="Test Route",
            static_route_network="10.10.0.0/16",
            static_route_nexthop="192.168.1.1",
            static_route_distance=5,
        )

        assert result is not None
        assert result["name"] == "Test Route"
        assert result["static-route_network"] == "10.10.0.0/16"
        routing_manager._connection._invalidate_cache.assert_called()

    @pytest.mark.asyncio
    async def test_create_route_minimal(self, routing_manager):
        """Test creating a static route with minimal parameters."""
        created_route = {
            "_id": "new_route_id",
            "name": "Basic Route",
            "static-route_network": "10.0.0.0/8",
            "static-route_nexthop": "192.168.1.1",
        }
        routing_manager._connection.request = AsyncMock(return_value=[created_route])

        result = await routing_manager.create_route(
            name="Basic Route",
            static_route_network="10.0.0.0/8",
            static_route_nexthop="192.168.1.1",
        )

        assert result is not None
        call_args = routing_manager._connection.request.call_args[0][0]
        assert call_args.data["name"] == "Basic Route"
        assert call_args.data["static-route_network"] == "10.0.0.0/8"

    @pytest.mark.asyncio
    async def test_create_route_api_error(self, routing_manager):
        """Test handling API errors during route creation."""
        routing_manager._connection.request = AsyncMock(
            side_effect=Exception("API Error")
        )

        result = await routing_manager.create_route(
            name="Test Route",
            static_route_network="10.0.0.0/8",
            static_route_nexthop="192.168.1.1",
        )

        assert result is None


class TestRoutingManagerUpdateRoute:
    """Test suite for RoutingManager.update_route method."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mock ConnectionManager."""
        mock = MagicMock()
        mock.ensure_connected = AsyncMock(return_value=True)
        mock.controller = MagicMock()
        mock.site = "default"
        mock.request = AsyncMock(return_value=None)
        mock._invalidate_cache = MagicMock()
        mock.get_cached = MagicMock(return_value=None)
        mock._update_cache = MagicMock()
        return mock

    @pytest.fixture
    def routing_manager(self, mock_connection_manager):
        """Create a RoutingManager with mocked connection."""
        return RoutingManager(mock_connection_manager)

    @pytest.mark.asyncio
    async def test_update_route_success(self, routing_manager):
        """Test successfully updating a static route."""
        existing_route = {
            "_id": "route_id",
            "name": "Old Name",
            "static-route_network": "10.0.0.0/8",
            "static-route_nexthop": "192.168.1.1",
            "static-route_distance": 1,
            "enabled": True,
        }

        with patch.object(
            routing_manager, "get_route_details", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = existing_route

            result = await routing_manager.update_route(
                route_id="route_id",
                name="New Name",
                static_route_distance=5,
            )

            assert result is True
            call_args = routing_manager._connection.request.call_args[0][0]
            assert call_args.data["name"] == "New Name"
            assert call_args.data["static-route_distance"] == 5
            routing_manager._connection._invalidate_cache.assert_called()

    @pytest.mark.asyncio
    async def test_update_route_not_found(self, routing_manager):
        """Test updating a non-existent static route."""
        with patch.object(
            routing_manager, "get_route_details", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            result = await routing_manager.update_route(
                route_id="nonexistent",
                name="New Name",
            )

            assert result is False
            routing_manager._connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_route_api_error(self, routing_manager):
        """Test handling API errors during route update."""
        existing_route = {"_id": "route_id", "name": "Test"}

        with patch.object(
            routing_manager, "get_route_details", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = existing_route
            routing_manager._connection.request = AsyncMock(
                side_effect=Exception("API Error")
            )

            result = await routing_manager.update_route(
                route_id="route_id",
                name="New Name",
            )

            assert result is False


class TestRoutingManagerDeleteRoute:
    """Test suite for RoutingManager.delete_route method."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mock ConnectionManager."""
        mock = MagicMock()
        mock.site = "default"
        mock.request = AsyncMock(return_value=None)
        mock._invalidate_cache = MagicMock()
        mock.get_cached = MagicMock(return_value=None)
        mock._update_cache = MagicMock()
        return mock

    @pytest.fixture
    def routing_manager(self, mock_connection_manager):
        """Create a RoutingManager with mocked connection."""
        return RoutingManager(mock_connection_manager)

    @pytest.mark.asyncio
    async def test_delete_route_success(self, routing_manager):
        """Test successfully deleting a static route."""
        existing_route = {"_id": "route_id", "name": "Test Route"}

        with patch.object(
            routing_manager, "get_route_details", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = existing_route

            result = await routing_manager.delete_route("route_id")

            assert result is True
            call_args = routing_manager._connection.request.call_args[0][0]
            assert call_args.method == "delete"
            assert "/rest/routing/route_id" in call_args.path

    @pytest.mark.asyncio
    async def test_delete_route_not_found(self, routing_manager):
        """Test deleting a non-existent static route."""
        with patch.object(
            routing_manager, "get_route_details", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            result = await routing_manager.delete_route("nonexistent")

            assert result is False


class TestRoutingManagerGetByName:
    """Test suite for RoutingManager.get_route_by_name method."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mock ConnectionManager."""
        mock = MagicMock()
        mock.site = "default"
        mock.request = AsyncMock(return_value=[])
        mock.get_cached = MagicMock(return_value=None)
        mock._update_cache = MagicMock()
        return mock

    @pytest.fixture
    def routing_manager(self, mock_connection_manager):
        """Create a RoutingManager with mocked connection."""
        return RoutingManager(mock_connection_manager)

    @pytest.mark.asyncio
    async def test_get_by_name_found(self, routing_manager):
        """Test finding a static route by name."""
        routes = [
            {"_id": "id1", "name": "VPN Route"},
            {"_id": "id2", "name": "Office Route"},
        ]

        with patch.object(
            routing_manager, "get_routes", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = routes

            result = await routing_manager.get_route_by_name("Office Route")

            assert result is not None
            assert result["_id"] == "id2"

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(self, routing_manager):
        """Test getting a non-existent static route by name."""
        with patch.object(
            routing_manager, "get_routes", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [{"_id": "id1", "name": "VPN Route"}]

            result = await routing_manager.get_route_by_name("Nonexistent")

            assert result is None
