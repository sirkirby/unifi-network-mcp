"""GET routes for active routes, static routes, and traffic routes.

Phase 5A PR1 Cluster 3 — networks/WLANs/VPN/DNS/routing.
Three resources in one module since they all live in the routing domain.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

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


# ---------- active routes ----------


@router.get(
    "/sites/{site_id}/active-routes",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def list_active_routes(
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
            session, controller.id, "network", "routing_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        if cm.site != site_id:
            await cm.set_site(site_id)
        items = await mgr.get_active_routes()

    cursor_obj = _decode_cursor(cursor)
    page, next_cursor = paginate(
        list(items), limit=limit, cursor=cursor_obj, key_fn=_id_key,
    )
    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("unifi_list_active_routes")
    return {
        "items": [serializer.serialize(i) for i in page],
        "next_cursor": next_cursor.encode() if next_cursor else None,
        "render_hint": registry.render_hint_for_tool("unifi_list_active_routes"),
    }


# ---------- static routes ----------


@router.get(
    "/sites/{site_id}/static-routes",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def list_routes(
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
            session, controller.id, "network", "routing_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        if cm.site != site_id:
            await cm.set_site(site_id)
        items = await mgr.get_routes()

    cursor_obj = _decode_cursor(cursor)
    page, next_cursor = paginate(
        list(items), limit=limit, cursor=cursor_obj, key_fn=_id_key,
    )
    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("unifi_list_routes")
    return {
        "items": [serializer.serialize(i) for i in page],
        "next_cursor": next_cursor.encode() if next_cursor else None,
        "render_hint": registry.render_hint_for_tool("unifi_list_routes"),
    }


@router.get(
    "/sites/{site_id}/static-routes/{route_id}",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_route_details(
    request: Request,
    site_id: str,
    route_id: str,
    controller=Depends(resolve_controller),
) -> dict:
    require_capability(controller, "network")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    async with sm() as session:
        mgr = await factory.get_domain_manager(
            session, controller.id, "network", "routing_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        if cm.site != site_id:
            await cm.set_site(site_id)
        item = await mgr.get_route_details(route_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"route {route_id} not found")
    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("unifi_get_route_details")
    return {
        "data": serializer.serialize(item),
        "render_hint": registry.render_hint_for_tool("unifi_get_route_details"),
    }


# ---------- traffic routes ----------


@router.get(
    "/sites/{site_id}/traffic-routes",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def list_traffic_routes(
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
            session, controller.id, "network", "traffic_route_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        if cm.site != site_id:
            await cm.set_site(site_id)
        items = await mgr.get_traffic_routes()

    cursor_obj = _decode_cursor(cursor)
    page, next_cursor = paginate(
        list(items), limit=limit, cursor=cursor_obj, key_fn=_id_key,
    )
    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("unifi_list_traffic_routes")
    return {
        "items": [serializer.serialize(i) for i in page],
        "next_cursor": next_cursor.encode() if next_cursor else None,
        "render_hint": registry.render_hint_for_tool("unifi_list_traffic_routes"),
    }


@router.get(
    "/sites/{site_id}/traffic-routes/{route_id}",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_traffic_route_details(
    request: Request,
    site_id: str,
    route_id: str,
    controller=Depends(resolve_controller),
) -> dict:
    require_capability(controller, "network")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    async with sm() as session:
        mgr = await factory.get_domain_manager(
            session, controller.id, "network", "traffic_route_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        if cm.site != site_id:
            await cm.set_site(site_id)
        item = await mgr.get_traffic_route_details(route_id)
    if item is None:
        raise HTTPException(
            status_code=404, detail=f"traffic route {route_id} not found",
        )
    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("unifi_get_traffic_route_details")
    return {
        "data": serializer.serialize(item),
        "render_hint": registry.render_hint_for_tool("unifi_get_traffic_route_details"),
    }
