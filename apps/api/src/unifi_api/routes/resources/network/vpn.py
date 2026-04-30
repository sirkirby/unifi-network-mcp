"""GET routes for VPN clients and VPN servers.

Phase 5A PR1 Cluster 3 — networks/WLANs/VPN/DNS/routing.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from unifi_core.exceptions import UniFiNotFoundError

from unifi_api.auth.middleware import require_scope
from unifi_api.auth.scopes import Scope
from unifi_api.routes.resources._common import (
    require_capability,
    resolve_controller,
)
from unifi_api.services.pagination import Cursor, InvalidCursor, paginate


router = APIRouter()


def _id_key(obj) -> tuple:
    raw = obj if isinstance(obj, dict) else getattr(obj, "raw", {}) or {}
    return (0, raw.get("_id") or raw.get("id") or "")


def _decode_cursor(cursor: str | None) -> Cursor | None:
    if not cursor:
        return None
    try:
        return Cursor.decode(cursor)
    except InvalidCursor:
        raise HTTPException(status_code=400, detail="invalid cursor")


# ---------- VPN clients ----------


@router.get(
    "/sites/{site_id}/vpn-clients",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def list_vpn_clients(
    request: Request,
    site_id: str,
    controller=Depends(resolve_controller),
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None),
) -> dict:
    require_capability(controller, "network")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    async with sm() as session:
        mgr = await factory.get_domain_manager(
            session, controller.id, "network", "vpn_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        if cm.site != site_id:
            await cm.set_site(site_id)
        items = await mgr.get_vpn_clients()

    cursor_obj = _decode_cursor(cursor)
    page, next_cursor = paginate(
        list(items), limit=limit, cursor=cursor_obj, key_fn=_id_key,
    )
    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("unifi_list_vpn_clients")
    return {
        "items": [serializer.serialize(i) for i in page],
        "next_cursor": next_cursor.encode() if next_cursor else None,
        "render_hint": registry.render_hint_for_tool("unifi_list_vpn_clients"),
    }


@router.get(
    "/sites/{site_id}/vpn-clients/{client_id}",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_vpn_client_details(
    request: Request,
    site_id: str,
    client_id: str,
    controller=Depends(resolve_controller),
) -> dict:
    require_capability(controller, "network")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    try:
        async with sm() as session:
            mgr = await factory.get_domain_manager(
                session, controller.id, "network", "vpn_manager",
            )
            cm = await factory.get_connection_manager(session, controller.id, "network")
            if cm.site != site_id:
                await cm.set_site(site_id)
            item = await mgr.get_vpn_client_details(client_id)
    except UniFiNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if item is None:
        raise HTTPException(
            status_code=404, detail=f"vpn client {client_id} not found",
        )
    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("unifi_get_vpn_client_details")
    return {
        "data": serializer.serialize(item),
        "render_hint": registry.render_hint_for_tool("unifi_get_vpn_client_details"),
    }


# ---------- VPN servers ----------


@router.get(
    "/sites/{site_id}/vpn-servers",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def list_vpn_servers(
    request: Request,
    site_id: str,
    controller=Depends(resolve_controller),
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None),
) -> dict:
    require_capability(controller, "network")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    async with sm() as session:
        mgr = await factory.get_domain_manager(
            session, controller.id, "network", "vpn_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        if cm.site != site_id:
            await cm.set_site(site_id)
        items = await mgr.get_vpn_servers()

    cursor_obj = _decode_cursor(cursor)
    page, next_cursor = paginate(
        list(items), limit=limit, cursor=cursor_obj, key_fn=_id_key,
    )
    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("unifi_list_vpn_servers")
    return {
        "items": [serializer.serialize(i) for i in page],
        "next_cursor": next_cursor.encode() if next_cursor else None,
        "render_hint": registry.render_hint_for_tool("unifi_list_vpn_servers"),
    }


@router.get(
    "/sites/{site_id}/vpn-servers/{server_id}",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_vpn_server_details(
    request: Request,
    site_id: str,
    server_id: str,
    controller=Depends(resolve_controller),
) -> dict:
    require_capability(controller, "network")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    try:
        async with sm() as session:
            mgr = await factory.get_domain_manager(
                session, controller.id, "network", "vpn_manager",
            )
            cm = await factory.get_connection_manager(session, controller.id, "network")
            if cm.site != site_id:
                await cm.set_site(site_id)
            item = await mgr.get_vpn_server_details(server_id)
    except UniFiNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if item is None:
        raise HTTPException(
            status_code=404, detail=f"vpn server {server_id} not found",
        )
    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("unifi_get_vpn_server_details")
    return {
        "data": serializer.serialize(item),
        "render_hint": registry.render_hint_for_tool("unifi_get_vpn_server_details"),
    }
