"""Tests for VisitorManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unifi_access_mcp.managers.connection_manager import AccessConnectionManager
from unifi_access_mcp.managers.visitor_manager import VisitorManager
from unifi_core.exceptions import UniFiConnectionError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cm_proxy():
    cm = AccessConnectionManager(host="192.168.1.1", username="admin", password="secret")
    cm._proxy_available = True
    cm._proxy_session = MagicMock()
    return cm


@pytest.fixture
def cm_none():
    return AccessConnectionManager(host="192.168.1.1", username="", password="")


@pytest.fixture
def visitor_mgr(cm_proxy):
    return VisitorManager(cm_proxy)


@pytest.fixture
def visitor_mgr_none(cm_none):
    return VisitorManager(cm_none)


# ---------------------------------------------------------------------------
# list_visitors
# ---------------------------------------------------------------------------


class TestListVisitors:
    @pytest.mark.asyncio
    async def test_list_visitors_success(self, visitor_mgr, cm_proxy):
        expected = [{"id": "vis-1", "name": "John Doe"}]
        with patch.object(cm_proxy, "proxy_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"data": expected}
            result = await visitor_mgr.list_visitors()
        assert result == expected

    @pytest.mark.asyncio
    async def test_list_visitors_no_proxy(self, visitor_mgr_none):
        with pytest.raises(UniFiConnectionError, match="No proxy session"):
            await visitor_mgr_none.list_visitors()


# ---------------------------------------------------------------------------
# get_visitor
# ---------------------------------------------------------------------------


class TestGetVisitor:
    @pytest.mark.asyncio
    async def test_get_visitor_success(self, visitor_mgr, cm_proxy):
        expected = {"id": "vis-1", "name": "John Doe", "status": "active"}
        with patch.object(cm_proxy, "proxy_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"data": expected}
            result = await visitor_mgr.get_visitor("vis-1")
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_visitor_empty_id(self, visitor_mgr):
        with pytest.raises(ValueError, match="visitor_id is required"):
            await visitor_mgr.get_visitor("")

    @pytest.mark.asyncio
    async def test_get_visitor_no_proxy(self, visitor_mgr_none):
        with pytest.raises(UniFiConnectionError, match="No proxy session"):
            await visitor_mgr_none.get_visitor("vis-1")


# ---------------------------------------------------------------------------
# create_visitor (preview)
# ---------------------------------------------------------------------------


class TestCreateVisitor:
    @pytest.mark.asyncio
    async def test_create_visitor_preview(self, visitor_mgr):
        preview = await visitor_mgr.create_visitor(
            name="Jane Doe",
            access_start="2026-03-17T09:00:00Z",
            access_end="2026-03-17T17:00:00Z",
        )
        assert preview["visitor_data"]["name"] == "Jane Doe"
        assert preview["proposed_changes"]["action"] == "create"

    @pytest.mark.asyncio
    async def test_create_visitor_with_extra(self, visitor_mgr):
        preview = await visitor_mgr.create_visitor(
            name="Jane Doe",
            access_start="2026-03-17T09:00:00Z",
            access_end="2026-03-17T17:00:00Z",
            email="jane@example.com",
        )
        assert preview["visitor_data"]["email"] == "jane@example.com"

    @pytest.mark.asyncio
    async def test_create_visitor_empty_name(self, visitor_mgr):
        with pytest.raises(ValueError, match="name is required"):
            await visitor_mgr.create_visitor(
                name="",
                access_start="2026-03-17T09:00:00Z",
                access_end="2026-03-17T17:00:00Z",
            )

    @pytest.mark.asyncio
    async def test_create_visitor_empty_times(self, visitor_mgr):
        with pytest.raises(ValueError, match="access_start and access_end are required"):
            await visitor_mgr.create_visitor(
                name="Jane",
                access_start="",
                access_end="",
            )


# ---------------------------------------------------------------------------
# apply_create_visitor
# ---------------------------------------------------------------------------


class TestApplyCreateVisitor:
    @pytest.mark.asyncio
    async def test_apply_create_success(self, visitor_mgr, cm_proxy):
        with patch.object(cm_proxy, "proxy_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"data": {"id": "vis-new"}}
            result = await visitor_mgr.apply_create_visitor(
                name="Jane Doe",
                access_start="2026-03-17T09:00:00Z",
                access_end="2026-03-17T17:00:00Z",
            )
        assert result["result"] == "success"

    @pytest.mark.asyncio
    async def test_apply_create_no_proxy(self, visitor_mgr_none):
        with pytest.raises(UniFiConnectionError, match="No proxy session"):
            await visitor_mgr_none.apply_create_visitor(
                name="Jane",
                access_start="2026-03-17T09:00:00Z",
                access_end="2026-03-17T17:00:00Z",
            )


# ---------------------------------------------------------------------------
# delete_visitor (preview)
# ---------------------------------------------------------------------------


class TestDeleteVisitor:
    @pytest.mark.asyncio
    async def test_delete_visitor_preview(self, visitor_mgr, cm_proxy):
        current = {"id": "vis-1", "name": "John Doe", "status": "active"}
        with patch.object(cm_proxy, "proxy_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"data": current}
            preview = await visitor_mgr.delete_visitor("vis-1")
        assert preview["visitor_id"] == "vis-1"
        assert preview["visitor_name"] == "John Doe"
        assert preview["proposed_changes"]["action"] == "delete"

    @pytest.mark.asyncio
    async def test_delete_visitor_empty_id(self, visitor_mgr):
        with pytest.raises(ValueError, match="visitor_id is required"):
            await visitor_mgr.delete_visitor("")


# ---------------------------------------------------------------------------
# apply_delete_visitor
# ---------------------------------------------------------------------------


class TestApplyDeleteVisitor:
    @pytest.mark.asyncio
    async def test_apply_delete_success(self, visitor_mgr, cm_proxy):
        with patch.object(cm_proxy, "proxy_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {}
            result = await visitor_mgr.apply_delete_visitor("vis-1")
        assert result["result"] == "success"
        assert result["action"] == "delete"

    @pytest.mark.asyncio
    async def test_apply_delete_no_proxy(self, visitor_mgr_none):
        with pytest.raises(UniFiConnectionError, match="No proxy session"):
            await visitor_mgr_none.apply_delete_visitor("vis-1")
