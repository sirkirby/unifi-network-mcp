"""Tests for the ContentFilterManager class.

This module tests content filtering profile operations.
Note: The UniFi API does not support POST (create) or GET /{id}.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestContentFilterManager:
    """Tests for the ContentFilterManager class."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock ConnectionManager."""
        conn = MagicMock()
        conn.site = "default"
        conn.request = AsyncMock()
        conn.get_cached = MagicMock(return_value=None)
        conn._update_cache = MagicMock()
        conn._invalidate_cache = MagicMock()
        conn.ensure_connected = AsyncMock(return_value=True)
        return conn

    @pytest.fixture
    def content_filter_manager(self, mock_connection):
        """Create a ContentFilterManager with mocked connection."""
        from unifi_network_mcp.managers.content_filter_manager import ContentFilterManager

        return ContentFilterManager(mock_connection)

    # ---- get_content_filters ----

    @pytest.mark.asyncio
    async def test_get_content_filters_returns_list(self, content_filter_manager, mock_connection):
        """Test get_content_filters returns a list of profiles."""
        mock_filters = [
            {"_id": "f1", "name": "Kids", "enabled": True, "categories": ["FAMILY"]},
            {"_id": "f2", "name": "All Internal", "enabled": True, "categories": ["MALWARE"]},
        ]
        mock_connection.request.return_value = mock_filters

        filters = await content_filter_manager.get_content_filters()

        assert len(filters) == 2
        assert filters[0]["name"] == "Kids"
        mock_connection._update_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_content_filters_uses_cache(self, content_filter_manager, mock_connection):
        """Test get_content_filters returns cached data when available."""
        cached = [{"_id": "cached", "name": "Cached Filter"}]
        mock_connection.get_cached.return_value = cached

        filters = await content_filter_manager.get_content_filters()

        assert filters == cached
        mock_connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_content_filters_handles_error(self, content_filter_manager, mock_connection):
        """Test get_content_filters returns empty list on error."""
        mock_connection.request.side_effect = Exception("Network error")

        filters = await content_filter_manager.get_content_filters()

        assert filters == []

    @pytest.mark.asyncio
    async def test_get_content_filters_not_connected(self, content_filter_manager, mock_connection):
        """Test get_content_filters returns empty list when not connected."""
        mock_connection.ensure_connected.return_value = False

        filters = await content_filter_manager.get_content_filters()

        assert filters == []
        mock_connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_content_filters_handles_dict_response(self, content_filter_manager, mock_connection):
        """Test get_content_filters handles dict response with data key."""
        mock_connection.request.return_value = {"data": [{"_id": "f1", "name": "Filter"}]}

        filters = await content_filter_manager.get_content_filters()

        assert len(filters) == 1

    # ---- get_content_filter_by_id ----

    @pytest.mark.asyncio
    async def test_get_content_filter_by_id_found(self, content_filter_manager, mock_connection):
        """Test get_content_filter_by_id returns profile when found via list search."""
        mock_connection.request.return_value = [
            {"_id": "f1", "name": "Kids", "categories": ["FAMILY"]},
            {"_id": "f2", "name": "All Internal", "categories": ["MALWARE"]},
        ]

        profile = await content_filter_manager.get_content_filter_by_id("f1")

        assert profile is not None
        assert profile["name"] == "Kids"

    @pytest.mark.asyncio
    async def test_get_content_filter_by_id_not_found(self, content_filter_manager, mock_connection):
        """Test get_content_filter_by_id returns None when ID not in list."""
        mock_connection.request.return_value = [
            {"_id": "f1", "name": "Kids"},
        ]

        profile = await content_filter_manager.get_content_filter_by_id("nonexistent")

        assert profile is None

    @pytest.mark.asyncio
    async def test_get_content_filter_by_id_handles_error(self, content_filter_manager, mock_connection):
        """Test get_content_filter_by_id returns None on error."""
        mock_connection.request.side_effect = Exception("API error")

        profile = await content_filter_manager.get_content_filter_by_id("f1")

        assert profile is None

    # ---- update_content_filter ----

    @pytest.mark.asyncio
    async def test_update_content_filter_success(self, content_filter_manager, mock_connection):
        """Test update_content_filter with valid data."""
        mock_connection.request.return_value = {}

        result = await content_filter_manager.update_content_filter(
            "f1", {"_id": "f1", "name": "Updated", "categories": ["FAMILY"]}
        )

        assert result is True
        mock_connection._invalidate_cache.assert_called()

    @pytest.mark.asyncio
    async def test_update_content_filter_not_connected(self, content_filter_manager, mock_connection):
        """Test update_content_filter returns False when not connected."""
        mock_connection.ensure_connected.return_value = False

        result = await content_filter_manager.update_content_filter("f1", {"name": "Test"})

        assert result is False

    @pytest.mark.asyncio
    async def test_update_content_filter_handles_error(self, content_filter_manager, mock_connection):
        """Test update_content_filter returns False on error."""
        mock_connection.request.side_effect = Exception("API error")

        result = await content_filter_manager.update_content_filter("f1", {"name": "Test"})

        assert result is False

    # ---- delete_content_filter ----

    @pytest.mark.asyncio
    async def test_delete_content_filter_success(self, content_filter_manager, mock_connection):
        """Test delete_content_filter with valid ID."""
        mock_connection.request.return_value = {}

        result = await content_filter_manager.delete_content_filter("f1")

        assert result is True
        mock_connection._invalidate_cache.assert_called()

    @pytest.mark.asyncio
    async def test_delete_content_filter_not_connected(self, content_filter_manager, mock_connection):
        """Test delete_content_filter returns False when not connected."""
        mock_connection.ensure_connected.return_value = False

        result = await content_filter_manager.delete_content_filter("f1")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_content_filter_handles_error(self, content_filter_manager, mock_connection):
        """Test delete_content_filter returns False on error."""
        mock_connection.request.side_effect = Exception("API error")

        result = await content_filter_manager.delete_content_filter("f1")

        assert result is False

    # ---- API path verification ----

    @pytest.mark.asyncio
    async def test_list_uses_correct_path(self, content_filter_manager, mock_connection):
        """Test get_content_filters calls the correct API endpoint."""
        mock_connection.request.return_value = []

        await content_filter_manager.get_content_filters()

        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.path == "/content-filtering"

    @pytest.mark.asyncio
    async def test_get_by_id_uses_list(self, content_filter_manager, mock_connection):
        """Test get_content_filter_by_id searches via list (no direct GET /{id})."""
        mock_connection.request.return_value = [{"_id": "f1", "name": "Test"}]

        await content_filter_manager.get_content_filter_by_id("f1")

        # Should call the list endpoint, not /content-filtering/f1
        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.path == "/content-filtering"

    @pytest.mark.asyncio
    async def test_update_uses_correct_path_and_method(self, content_filter_manager, mock_connection):
        """Test update_content_filter uses PUT to the correct endpoint."""
        mock_connection.request.return_value = {}

        await content_filter_manager.update_content_filter("f1", {"name": "Updated"})

        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.path == "/content-filtering/f1"
        assert api_request.method == "put"

    @pytest.mark.asyncio
    async def test_delete_uses_correct_path_and_method(self, content_filter_manager, mock_connection):
        """Test delete_content_filter uses DELETE to the correct endpoint."""
        mock_connection.request.return_value = {}

        await content_filter_manager.delete_content_filter("f1")

        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.path == "/content-filtering/f1"
        assert api_request.method == "delete"
