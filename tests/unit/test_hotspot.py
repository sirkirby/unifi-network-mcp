"""Unit tests for hotspot voucher functionality.

Tests the HotspotManager methods and the corresponding MCP tools.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.managers.hotspot_manager import HotspotManager


class TestHotspotManagerGetVouchers:
    """Test suite for HotspotManager.get_vouchers method."""

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
    def hotspot_manager(self, mock_connection_manager):
        """Create a HotspotManager with mocked connection."""
        return HotspotManager(mock_connection_manager)

    @pytest.fixture
    def sample_vouchers(self):
        """Sample voucher data returned by the API."""
        return [
            {
                "_id": "voucher_id_1",
                "code": "12345-67890",
                "quota": 1,
                "duration": 1440,
                "used": 0,
                "note": "Guest WiFi",
                "create_time": 1700000000,
                "qos_overwrite": False,
            },
            {
                "_id": "voucher_id_2",
                "code": "11111-22222",
                "quota": 0,
                "duration": 480,
                "used": 3,
                "note": "Conference",
                "create_time": 1700000100,
                "qos_overwrite": True,
                "qos_rate_max_up": 1000,
                "qos_rate_max_down": 5000,
            },
        ]

    @pytest.mark.asyncio
    async def test_get_vouchers_success(self, hotspot_manager, sample_vouchers):
        """Test successfully getting vouchers."""
        hotspot_manager._connection.request = AsyncMock(return_value=sample_vouchers)

        result = await hotspot_manager.get_vouchers()

        assert len(result) == 2
        assert result[0]["code"] == "12345-67890"
        assert result[1]["code"] == "11111-22222"
        hotspot_manager._connection._update_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_vouchers_from_cache(self, hotspot_manager, sample_vouchers):
        """Test getting vouchers from cache."""
        hotspot_manager._connection.get_cached = MagicMock(return_value=sample_vouchers)

        result = await hotspot_manager.get_vouchers()

        assert len(result) == 2
        hotspot_manager._connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_vouchers_with_create_time_filter(
        self, hotspot_manager, sample_vouchers
    ):
        """Test filtering vouchers by create_time."""
        hotspot_manager._connection.request = AsyncMock(return_value=sample_vouchers)

        result = await hotspot_manager.get_vouchers(create_time=1700000000)

        assert len(result) == 1
        assert result[0]["code"] == "12345-67890"

    @pytest.mark.asyncio
    async def test_get_vouchers_empty(self, hotspot_manager):
        """Test getting vouchers when none exist."""
        hotspot_manager._connection.request = AsyncMock(return_value=[])

        result = await hotspot_manager.get_vouchers()

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_vouchers_api_error(self, hotspot_manager):
        """Test handling API errors gracefully."""
        hotspot_manager._connection.request = AsyncMock(
            side_effect=Exception("API Error")
        )

        result = await hotspot_manager.get_vouchers()

        assert result == []


class TestHotspotManagerCreateVoucher:
    """Test suite for HotspotManager.create_voucher method."""

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
    def hotspot_manager(self, mock_connection_manager):
        """Create a HotspotManager with mocked connection."""
        return HotspotManager(mock_connection_manager)

    @pytest.mark.asyncio
    async def test_create_voucher_success(self, hotspot_manager):
        """Test successfully creating a voucher."""
        create_response = [{"create_time": 1700000000}]
        created_voucher = [
            {
                "_id": "new_voucher_id",
                "code": "99999-88888",
                "quota": 1,
                "duration": 1440,
                "create_time": 1700000000,
            }
        ]

        # First call returns create response, second call returns the voucher
        hotspot_manager._connection.request = AsyncMock(return_value=create_response)
        hotspot_manager._connection.get_cached = MagicMock(return_value=None)

        # Mock get_vouchers to return the created voucher
        with patch.object(
            hotspot_manager, "get_vouchers", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = created_voucher

            result = await hotspot_manager.create_voucher(
                expire_minutes=1440,
                count=1,
                quota=1,
                note="Test voucher",
            )

            assert result is not None
            assert len(result) == 1
            assert result[0]["code"] == "99999-88888"
            hotspot_manager._connection._invalidate_cache.assert_called()

    @pytest.mark.asyncio
    async def test_create_voucher_with_limits(self, hotspot_manager):
        """Test creating a voucher with bandwidth limits."""
        create_response = [{"create_time": 1700000000}]
        hotspot_manager._connection.request = AsyncMock(return_value=create_response)

        with patch.object(
            hotspot_manager, "get_vouchers", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [{"_id": "test", "code": "12345"}]

            await hotspot_manager.create_voucher(
                expire_minutes=60,
                count=1,
                quota=1,
                up_limit_kbps=1000,
                down_limit_kbps=5000,
                bytes_limit_mb=100,
            )

            # Verify the request was called with the right payload
            call_args = hotspot_manager._connection.request.call_args[0][0]
            assert call_args.data["cmd"] == "create-voucher"
            assert call_args.data["expire"] == 60
            assert call_args.data["up"] == 1000
            assert call_args.data["down"] == 5000
            assert call_args.data["bytes"] == 100

    @pytest.mark.asyncio
    async def test_create_voucher_multiple(self, hotspot_manager):
        """Test creating multiple vouchers."""
        create_response = [{"create_time": 1700000000}]
        hotspot_manager._connection.request = AsyncMock(return_value=create_response)

        with patch.object(
            hotspot_manager, "get_vouchers", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [
                {"_id": "v1", "code": "11111"},
                {"_id": "v2", "code": "22222"},
                {"_id": "v3", "code": "33333"},
            ]

            result = await hotspot_manager.create_voucher(
                expire_minutes=480,
                count=3,
                quota=1,
            )

            assert result is not None
            assert len(result) == 3

            call_args = hotspot_manager._connection.request.call_args[0][0]
            assert call_args.data["n"] == 3

    @pytest.mark.asyncio
    async def test_create_voucher_api_error(self, hotspot_manager):
        """Test handling API errors during voucher creation."""
        hotspot_manager._connection.request = AsyncMock(
            side_effect=Exception("API Error")
        )

        result = await hotspot_manager.create_voucher(
            expire_minutes=60,
            count=1,
            quota=1,
        )

        assert result is None


class TestHotspotManagerRevokeVoucher:
    """Test suite for HotspotManager.revoke_voucher method."""

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
    def hotspot_manager(self, mock_connection_manager):
        """Create a HotspotManager with mocked connection."""
        return HotspotManager(mock_connection_manager)

    @pytest.mark.asyncio
    async def test_revoke_voucher_success(self, hotspot_manager):
        """Test successfully revoking a voucher."""
        hotspot_manager._connection.request = AsyncMock(return_value=None)

        result = await hotspot_manager.revoke_voucher("voucher_id_123")

        assert result is True
        call_args = hotspot_manager._connection.request.call_args[0][0]
        assert call_args.data["cmd"] == "delete-voucher"
        assert call_args.data["_id"] == "voucher_id_123"
        hotspot_manager._connection._invalidate_cache.assert_called()

    @pytest.mark.asyncio
    async def test_revoke_voucher_api_error(self, hotspot_manager):
        """Test handling API errors during voucher revocation."""
        hotspot_manager._connection.request = AsyncMock(
            side_effect=Exception("API Error")
        )

        result = await hotspot_manager.revoke_voucher("voucher_id_123")

        assert result is False


class TestHotspotManagerGetVoucherDetails:
    """Test suite for HotspotManager.get_voucher_details method."""

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
    def hotspot_manager(self, mock_connection_manager):
        """Create a HotspotManager with mocked connection."""
        return HotspotManager(mock_connection_manager)

    @pytest.mark.asyncio
    async def test_get_voucher_details_found(self, hotspot_manager):
        """Test getting details for an existing voucher."""
        vouchers = [
            {"_id": "voucher_1", "code": "11111"},
            {"_id": "voucher_2", "code": "22222"},
        ]

        with patch.object(
            hotspot_manager, "get_vouchers", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = vouchers

            result = await hotspot_manager.get_voucher_details("voucher_2")

            assert result is not None
            assert result["code"] == "22222"

    @pytest.mark.asyncio
    async def test_get_voucher_details_not_found(self, hotspot_manager):
        """Test getting details for a non-existent voucher."""
        with patch.object(
            hotspot_manager, "get_vouchers", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [{"_id": "other", "code": "11111"}]

            result = await hotspot_manager.get_voucher_details("nonexistent")

            assert result is None
