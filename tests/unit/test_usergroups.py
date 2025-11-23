"""Unit tests for user group functionality.

Tests the UserGroupManager methods for managing user groups and bandwidth limits.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.managers.usergroup_manager import UserGroupManager


class TestUserGroupManagerGetUsergroups:
    """Test suite for UserGroupManager.get_usergroups method."""

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
    def usergroup_manager(self, mock_connection_manager):
        """Create a UserGroupManager with mocked connection."""
        return UserGroupManager(mock_connection_manager)

    @pytest.fixture
    def sample_usergroups(self):
        """Sample user group data returned by the API."""
        return [
            {
                "_id": "default_group_id",
                "name": "Default",
                "qos_rate_max_down": -1,
                "qos_rate_max_up": -1,
                "attr_no_delete": True,
                "site_id": "site123",
            },
            {
                "_id": "limited_group_id",
                "name": "Limited Guests",
                "qos_rate_max_down": 10000,
                "qos_rate_max_up": 2000,
                "attr_no_delete": False,
                "site_id": "site123",
            },
        ]

    @pytest.mark.asyncio
    async def test_get_usergroups_success(self, usergroup_manager, sample_usergroups):
        """Test successfully getting user groups."""
        usergroup_manager._connection.request = AsyncMock(return_value=sample_usergroups)

        result = await usergroup_manager.get_usergroups()

        assert len(result) == 2
        assert result[0]["name"] == "Default"
        assert result[1]["name"] == "Limited Guests"
        usergroup_manager._connection._update_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_usergroups_from_cache(self, usergroup_manager, sample_usergroups):
        """Test getting user groups from cache."""
        usergroup_manager._connection.get_cached = MagicMock(return_value=sample_usergroups)

        result = await usergroup_manager.get_usergroups()

        assert len(result) == 2
        usergroup_manager._connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_usergroups_empty(self, usergroup_manager):
        """Test getting user groups when none exist."""
        usergroup_manager._connection.request = AsyncMock(return_value=[])

        result = await usergroup_manager.get_usergroups()

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_usergroups_api_error(self, usergroup_manager):
        """Test handling API errors gracefully."""
        usergroup_manager._connection.request = AsyncMock(
            side_effect=Exception("API Error")
        )

        result = await usergroup_manager.get_usergroups()

        assert result == []


class TestUserGroupManagerCreateUsergroup:
    """Test suite for UserGroupManager.create_usergroup method."""

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
    def usergroup_manager(self, mock_connection_manager):
        """Create a UserGroupManager with mocked connection."""
        return UserGroupManager(mock_connection_manager)

    @pytest.mark.asyncio
    async def test_create_usergroup_success(self, usergroup_manager):
        """Test successfully creating a user group."""
        created_group = {
            "_id": "new_group_id",
            "name": "Test Group",
            "qos_rate_max_down": 5000,
            "qos_rate_max_up": 1000,
        }
        usergroup_manager._connection.request = AsyncMock(return_value=[created_group])

        result = await usergroup_manager.create_usergroup(
            name="Test Group",
            qos_rate_max_down=5000,
            qos_rate_max_up=1000,
        )

        assert result is not None
        assert result["name"] == "Test Group"
        assert result["qos_rate_max_down"] == 5000
        usergroup_manager._connection._invalidate_cache.assert_called()

    @pytest.mark.asyncio
    async def test_create_usergroup_minimal(self, usergroup_manager):
        """Test creating a user group with just a name."""
        created_group = {"_id": "new_group_id", "name": "Basic Group"}
        usergroup_manager._connection.request = AsyncMock(return_value=[created_group])

        result = await usergroup_manager.create_usergroup(name="Basic Group")

        assert result is not None
        call_args = usergroup_manager._connection.request.call_args[0][0]
        assert call_args.data["name"] == "Basic Group"
        assert "qos_rate_max_down" not in call_args.data

    @pytest.mark.asyncio
    async def test_create_usergroup_api_error(self, usergroup_manager):
        """Test handling API errors during user group creation."""
        usergroup_manager._connection.request = AsyncMock(
            side_effect=Exception("API Error")
        )

        result = await usergroup_manager.create_usergroup(name="Test Group")

        assert result is None


class TestUserGroupManagerUpdateUsergroup:
    """Test suite for UserGroupManager.update_usergroup method."""

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
    def usergroup_manager(self, mock_connection_manager):
        """Create a UserGroupManager with mocked connection."""
        return UserGroupManager(mock_connection_manager)

    @pytest.mark.asyncio
    async def test_update_usergroup_success(self, usergroup_manager):
        """Test successfully updating a user group."""
        existing_group = {
            "_id": "group_id",
            "name": "Old Name",
            "qos_rate_max_down": -1,
            "qos_rate_max_up": -1,
        }

        with patch.object(
            usergroup_manager, "get_usergroup_details", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = existing_group

            result = await usergroup_manager.update_usergroup(
                group_id="group_id",
                name="New Name",
                qos_rate_max_down=10000,
            )

            assert result is True
            call_args = usergroup_manager._connection.request.call_args[0][0]
            assert call_args.data["name"] == "New Name"
            assert call_args.data["qos_rate_max_down"] == 10000
            usergroup_manager._connection._invalidate_cache.assert_called()

    @pytest.mark.asyncio
    async def test_update_usergroup_not_found(self, usergroup_manager):
        """Test updating a non-existent user group."""
        with patch.object(
            usergroup_manager, "get_usergroup_details", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            result = await usergroup_manager.update_usergroup(
                group_id="nonexistent",
                name="New Name",
            )

            assert result is False
            usergroup_manager._connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_usergroup_api_error(self, usergroup_manager):
        """Test handling API errors during user group update."""
        existing_group = {"_id": "group_id", "name": "Test"}

        with patch.object(
            usergroup_manager, "get_usergroup_details", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = existing_group
            usergroup_manager._connection.request = AsyncMock(
                side_effect=Exception("API Error")
            )

            result = await usergroup_manager.update_usergroup(
                group_id="group_id",
                name="New Name",
            )

            assert result is False


class TestUserGroupManagerDeleteUsergroup:
    """Test suite for UserGroupManager.delete_usergroup method."""

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
    def usergroup_manager(self, mock_connection_manager):
        """Create a UserGroupManager with mocked connection."""
        return UserGroupManager(mock_connection_manager)

    @pytest.mark.asyncio
    async def test_delete_usergroup_success(self, usergroup_manager):
        """Test successfully deleting a user group."""
        existing_group = {"_id": "group_id", "name": "Test", "attr_no_delete": False}

        with patch.object(
            usergroup_manager, "get_usergroup_details", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = existing_group

            result = await usergroup_manager.delete_usergroup("group_id")

            assert result is True
            call_args = usergroup_manager._connection.request.call_args[0][0]
            assert call_args.method == "delete"
            assert "/rest/usergroup/group_id" in call_args.path

    @pytest.mark.asyncio
    async def test_delete_usergroup_protected(self, usergroup_manager):
        """Test that protected groups cannot be deleted."""
        protected_group = {"_id": "default_id", "name": "Default", "attr_no_delete": True}

        with patch.object(
            usergroup_manager, "get_usergroup_details", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = protected_group

            result = await usergroup_manager.delete_usergroup("default_id")

            assert result is False
            usergroup_manager._connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_usergroup_not_found(self, usergroup_manager):
        """Test deleting a non-existent user group."""
        with patch.object(
            usergroup_manager, "get_usergroup_details", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            result = await usergroup_manager.delete_usergroup("nonexistent")

            assert result is False


class TestUserGroupManagerGetByName:
    """Test suite for UserGroupManager.get_usergroup_by_name method."""

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
    def usergroup_manager(self, mock_connection_manager):
        """Create a UserGroupManager with mocked connection."""
        return UserGroupManager(mock_connection_manager)

    @pytest.mark.asyncio
    async def test_get_by_name_found(self, usergroup_manager):
        """Test finding a user group by name."""
        groups = [
            {"_id": "id1", "name": "Default"},
            {"_id": "id2", "name": "Guests"},
        ]

        with patch.object(
            usergroup_manager, "get_usergroups", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = groups

            result = await usergroup_manager.get_usergroup_by_name("Guests")

            assert result is not None
            assert result["_id"] == "id2"

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(self, usergroup_manager):
        """Test getting a non-existent user group by name."""
        with patch.object(
            usergroup_manager, "get_usergroups", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [{"_id": "id1", "name": "Default"}]

            result = await usergroup_manager.get_usergroup_by_name("Nonexistent")

            assert result is None
