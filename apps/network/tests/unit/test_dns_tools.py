"""Tests for DNS record tool functions.

Tests tool-layer behavior: validation, preview/confirm flow, response format.
Manager-level tests are in test_dns_manager.py.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("UNIFI_HOST", "127.0.0.1")
os.environ.setdefault("UNIFI_USERNAME", "test")
os.environ.setdefault("UNIFI_PASSWORD", "test")


SAMPLE_RECORD = {
    "_id": "dns001",
    "key": "host.example.com",
    "value": "10.0.0.1",
    "record_type": "A",
    "enabled": True,
    "ttl": 300,
}


# ---------------------------------------------------------------------------
# list_dns_records
# ---------------------------------------------------------------------------


class TestListDnsRecords:
    """Test the list_dns_records tool."""

    @pytest.mark.asyncio
    async def test_list_success(self):
        """List returns formatted records with success."""
        mock_conn = MagicMock()
        mock_conn.site = "default"

        with patch("unifi_network_mcp.tools.dns.dns_manager") as mock_mgr:
            mock_mgr.list_dns_records = AsyncMock(return_value=[SAMPLE_RECORD])
            mock_mgr._connection = mock_conn

            from unifi_network_mcp.tools.dns import list_dns_records

            result = await list_dns_records()

        assert result["success"] is True
        assert result["count"] == 1
        assert result["records"][0]["key"] == "host.example.com"
        assert result["records"][0]["id"] == "dns001"

    @pytest.mark.asyncio
    async def test_list_empty(self):
        """List returns zero count when no records exist."""
        mock_conn = MagicMock()
        mock_conn.site = "default"

        with patch("unifi_network_mcp.tools.dns.dns_manager") as mock_mgr:
            mock_mgr.list_dns_records = AsyncMock(return_value=[])
            mock_mgr._connection = mock_conn

            from unifi_network_mcp.tools.dns import list_dns_records

            result = await list_dns_records()

        assert result["success"] is True
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_list_exception(self):
        """List returns error on exception."""
        with patch("unifi_network_mcp.tools.dns.dns_manager") as mock_mgr:
            mock_mgr.list_dns_records = AsyncMock(side_effect=Exception("Connection lost"))

            from unifi_network_mcp.tools.dns import list_dns_records

            result = await list_dns_records()

        assert result["success"] is False
        assert "Failed to list" in result["error"]


# ---------------------------------------------------------------------------
# get_dns_record_details
# ---------------------------------------------------------------------------


class TestGetDnsRecordDetails:
    """Test the get_dns_record_details tool."""

    @pytest.mark.asyncio
    async def test_get_found(self):
        """Get returns record details when found."""
        with patch("unifi_network_mcp.tools.dns.dns_manager") as mock_mgr:
            mock_mgr.get_dns_record = AsyncMock(return_value=SAMPLE_RECORD)

            from unifi_network_mcp.tools.dns import get_dns_record_details

            result = await get_dns_record_details(record_id="dns001")

        assert result["success"] is True
        assert result["record_id"] == "dns001"
        assert result["details"]["key"] == "host.example.com"

    @pytest.mark.asyncio
    async def test_get_not_found(self):
        """Get returns error when record not found."""
        with patch("unifi_network_mcp.tools.dns.dns_manager") as mock_mgr:
            mock_mgr.get_dns_record = AsyncMock(return_value=None)

            from unifi_network_mcp.tools.dns import get_dns_record_details

            result = await get_dns_record_details(record_id="nonexistent")

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_exception(self):
        """Get returns error on exception."""
        with patch("unifi_network_mcp.tools.dns.dns_manager") as mock_mgr:
            mock_mgr.get_dns_record = AsyncMock(side_effect=Exception("Timeout"))

            from unifi_network_mcp.tools.dns import get_dns_record_details

            result = await get_dns_record_details(record_id="dns001")

        assert result["success"] is False
        assert "Failed to get" in result["error"]


# ---------------------------------------------------------------------------
# create_dns_record
# ---------------------------------------------------------------------------


class TestCreateDnsRecord:
    """Test the create_dns_record tool."""

    @pytest.mark.asyncio
    async def test_create_preview(self):
        """Preview mode returns confirmation prompt without creating."""
        from unifi_network_mcp.tools.dns import create_dns_record

        result = await create_dns_record(
            record_data={"key": "new.example.com", "value": "10.0.0.5", "record_type": "A"},
            confirm=False,
        )

        assert result["success"] is True
        assert result.get("requires_confirmation") is True

    @pytest.mark.asyncio
    async def test_create_confirm_success(self):
        """Confirmed create returns success with details."""
        created = {"_id": "dns_new", "key": "new.example.com", "value": "10.0.0.5", "record_type": "A"}

        with patch("unifi_network_mcp.tools.dns.dns_manager") as mock_mgr:
            mock_mgr.create_dns_record = AsyncMock(return_value=created)

            from unifi_network_mcp.tools.dns import create_dns_record

            result = await create_dns_record(
                record_data={"key": "new.example.com", "value": "10.0.0.5", "record_type": "A"},
                confirm=True,
            )

        assert result["success"] is True
        assert "created successfully" in result["message"]
        assert result["details"]["_id"] == "dns_new"

    @pytest.mark.asyncio
    async def test_create_validation_error(self):
        """Invalid record_type is rejected by schema validation."""
        from unifi_network_mcp.tools.dns import create_dns_record

        result = await create_dns_record(
            record_data={"key": "bad.example.com", "value": "10.0.0.1", "record_type": "INVALID"},
            confirm=True,
        )

        assert result["success"] is False
        assert "Validation error" in result["error"]

    @pytest.mark.asyncio
    async def test_create_missing_required_field(self):
        """Missing required field is rejected by schema validation."""
        from unifi_network_mcp.tools.dns import create_dns_record

        result = await create_dns_record(
            record_data={"key": "novalue.example.com", "record_type": "A"},
            confirm=True,
        )

        assert result["success"] is False
        assert "Validation error" in result["error"]

    @pytest.mark.asyncio
    async def test_create_manager_failure(self):
        """Manager returning None results in error response."""
        with patch("unifi_network_mcp.tools.dns.dns_manager") as mock_mgr:
            mock_mgr.create_dns_record = AsyncMock(return_value=None)

            from unifi_network_mcp.tools.dns import create_dns_record

            result = await create_dns_record(
                record_data={"key": "fail.example.com", "value": "10.0.0.1", "record_type": "A"},
                confirm=True,
            )

        assert result["success"] is False
        assert "Failed to create" in result["error"]

    @pytest.mark.asyncio
    async def test_create_rejects_additional_properties(self):
        """Schema with additionalProperties: false rejects unknown fields."""
        from unifi_network_mcp.tools.dns import create_dns_record

        result = await create_dns_record(
            record_data={
                "key": "test.example.com",
                "value": "10.0.0.1",
                "record_type": "A",
                "bogus_field": "should fail",
            },
            confirm=True,
        )

        assert result["success"] is False
        assert "Validation error" in result["error"]


# ---------------------------------------------------------------------------
# update_dns_record
# ---------------------------------------------------------------------------


class TestUpdateDnsRecord:
    """Test the update_dns_record tool."""

    @pytest.mark.asyncio
    async def test_update_preview(self):
        """Preview mode returns current state and proposed changes."""
        with patch("unifi_network_mcp.tools.dns.dns_manager") as mock_mgr:
            mock_mgr.get_dns_record = AsyncMock(return_value=SAMPLE_RECORD)

            from unifi_network_mcp.tools.dns import update_dns_record

            result = await update_dns_record(
                record_id="dns001",
                update_data={"value": "10.0.0.2"},
                confirm=False,
            )

        assert result["success"] is True
        assert result.get("requires_confirmation") is True

    @pytest.mark.asyncio
    async def test_update_confirm_success(self):
        """Confirmed update calls manager and returns success."""
        with patch("unifi_network_mcp.tools.dns.dns_manager") as mock_mgr:
            mock_mgr.get_dns_record = AsyncMock(return_value=SAMPLE_RECORD)
            mock_mgr.update_dns_record = AsyncMock(return_value=True)

            from unifi_network_mcp.tools.dns import update_dns_record

            result = await update_dns_record(
                record_id="dns001",
                update_data={"value": "10.0.0.2"},
                confirm=True,
            )

        assert result["success"] is True
        assert "updated successfully" in result["message"]

    @pytest.mark.asyncio
    async def test_update_not_found(self):
        """Update returns error when record not found."""
        with patch("unifi_network_mcp.tools.dns.dns_manager") as mock_mgr:
            mock_mgr.get_dns_record = AsyncMock(return_value=None)

            from unifi_network_mcp.tools.dns import update_dns_record

            result = await update_dns_record(
                record_id="nonexistent",
                update_data={"value": "10.0.0.2"},
                confirm=True,
            )

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_update_empty_data(self):
        """Empty update_data returns error."""
        from unifi_network_mcp.tools.dns import update_dns_record

        result = await update_dns_record(
            record_id="dns001",
            update_data={},
            confirm=True,
        )

        assert result["success"] is False
        assert "No fields provided" in result["error"]

    @pytest.mark.asyncio
    async def test_update_validation_error(self):
        """Invalid field type is rejected by schema."""
        from unifi_network_mcp.tools.dns import update_dns_record

        result = await update_dns_record(
            record_id="dns001",
            update_data={"record_type": "INVALID"},
            confirm=True,
        )

        assert result["success"] is False
        assert "Validation error" in result["error"]

    @pytest.mark.asyncio
    async def test_update_manager_failure(self):
        """Manager returning False results in error response."""
        with patch("unifi_network_mcp.tools.dns.dns_manager") as mock_mgr:
            mock_mgr.get_dns_record = AsyncMock(return_value=SAMPLE_RECORD)
            mock_mgr.update_dns_record = AsyncMock(return_value=False)

            from unifi_network_mcp.tools.dns import update_dns_record

            result = await update_dns_record(
                record_id="dns001",
                update_data={"value": "10.0.0.2"},
                confirm=True,
            )

        assert result["success"] is False
        assert "Failed to update" in result["error"]


# ---------------------------------------------------------------------------
# delete_dns_record
# ---------------------------------------------------------------------------


class TestDeleteDnsRecord:
    """Test the delete_dns_record tool."""

    @pytest.mark.asyncio
    async def test_delete_preview(self):
        """Preview mode returns confirmation prompt with warning."""
        with patch("unifi_network_mcp.tools.dns.dns_manager") as mock_mgr:
            mock_mgr.get_dns_record = AsyncMock(return_value=SAMPLE_RECORD)

            from unifi_network_mcp.tools.dns import delete_dns_record

            result = await delete_dns_record(record_id="dns001", confirm=False)

        assert result["success"] is True
        assert result.get("requires_confirmation") is True

    @pytest.mark.asyncio
    async def test_delete_confirm_success(self):
        """Confirmed delete calls manager and returns success."""
        with patch("unifi_network_mcp.tools.dns.dns_manager") as mock_mgr:
            mock_mgr.delete_dns_record = AsyncMock(return_value=True)

            from unifi_network_mcp.tools.dns import delete_dns_record

            result = await delete_dns_record(record_id="dns001", confirm=True)

        assert result["success"] is True
        assert "deleted successfully" in result["message"]
        mock_mgr.delete_dns_record.assert_called_once_with("dns001")

    @pytest.mark.asyncio
    async def test_delete_manager_failure(self):
        """Manager returning False results in error response."""
        with patch("unifi_network_mcp.tools.dns.dns_manager") as mock_mgr:
            mock_mgr.delete_dns_record = AsyncMock(return_value=False)

            from unifi_network_mcp.tools.dns import delete_dns_record

            result = await delete_dns_record(record_id="dns001", confirm=True)

        assert result["success"] is False
        assert "Failed to delete" in result["error"]

    @pytest.mark.asyncio
    async def test_delete_exception(self):
        """Exception returns clean error."""
        with patch("unifi_network_mcp.tools.dns.dns_manager") as mock_mgr:
            mock_mgr.delete_dns_record = AsyncMock(side_effect=Exception("Connection refused"))

            from unifi_network_mcp.tools.dns import delete_dns_record

            result = await delete_dns_record(record_id="dns001", confirm=True)

        assert result["success"] is False
        assert "Connection refused" in result["error"]
