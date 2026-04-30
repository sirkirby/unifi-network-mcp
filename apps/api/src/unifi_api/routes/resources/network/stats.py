"""GET /v1/sites/{site_id}/stats/* — network stats endpoints.

Phase 5A PR2 Cluster 6. Stats endpoints span TIMESERIES and DETAIL kinds.

Phase 4A registered 5 stats tools as TIMESERIES (dashboard, network, gateway,
site_dpi_traffic, client_dpi_traffic) and 3 as DETAIL (device_stats,
client_stats, dpi_stats) because Phase 2's AST captured the lookup method,
not the stats fetch method. The parallel manager-refactor will eventually
re-register the 3 DETAIL ones as TIMESERIES; the dual-kind handler below
makes Phase 5A robust to whichever state is current at request time.

For the 3 currently-DETAIL stats tools, we call the manager method that the
AST-derived dispatch table currently routes to (verified at module import
time): device_manager.get_device_details, client_manager.get_client_details,
stats_manager.get_dpi_stats. When the parallel refactor lands, both the
serializer kind and the dispatch table will update together — the route
inherits both via the registry/dispatch.
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


def _decode_cursor(cursor: str | None) -> Cursor | None:
    if not cursor:
        return None
    try:
        return Cursor.decode(cursor)
    except InvalidCursor:
        raise HTTPException(status_code=400, detail="invalid cursor")


def _ts_key(point) -> tuple:
    """Sort key for timeseries points: (ts, id) descending."""
    raw = point if isinstance(point, dict) else getattr(point, "raw", {}) or {}
    ts = raw.get("ts") or raw.get("time") or raw.get("timestamp") or 0
    return (ts, "")


def _stats_response(
    request: Request,
    payload,
    tool_name: str,
    *,
    limit: int,
    cursor: str | None,
) -> dict:
    """Dual-kind handler: TIMESERIES paginates per-point; DETAIL passes through."""
    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool(tool_name)
    kind = registry.kind_for_tool(tool_name)
    hint = registry.render_hint_for_tool(tool_name)

    if kind.value == "timeseries":
        items_raw = list(payload) if isinstance(payload, list) else []
        cursor_obj = _decode_cursor(cursor)
        page, next_cursor = paginate(
            items_raw, limit=limit, cursor=cursor_obj, key_fn=_ts_key,
        )
        return {
            "items": [serializer.serialize(p) for p in page],
            "next_cursor": next_cursor.encode() if next_cursor else None,
            "render_hint": hint,
        }
    # DETAIL kind (the 3 mis-classified stats tools at present).
    return {"data": serializer.serialize(payload), "render_hint": hint}


async def _maybe_set_site(cm, site_id: str) -> None:
    if getattr(cm, "site", None) != site_id:
        await cm.set_site(site_id)


# ---------- TIMESERIES — flat /stats/* paths ----------


@router.get(
    "/sites/{site_id}/stats/dashboard",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_dashboard_stats(
    request: Request,
    site_id: str,
    controller=Depends(resolve_controller),
    limit: int = Query(50, ge=1, le=500),
    cursor: str | None = Query(None),
) -> dict:
    require_capability(controller, "network")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    async with sm() as session:
        mgr = await factory.get_domain_manager(
            session, controller.id, "network", "stats_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        await _maybe_set_site(cm, site_id)
        payload = await mgr.get_dashboard()
    return _stats_response(
        request, payload, "unifi_get_dashboard", limit=limit, cursor=cursor,
    )


@router.get(
    "/sites/{site_id}/stats/network",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_network_stats(
    request: Request,
    site_id: str,
    controller=Depends(resolve_controller),
    limit: int = Query(50, ge=1, le=500),
    cursor: str | None = Query(None),
) -> dict:
    require_capability(controller, "network")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    async with sm() as session:
        mgr = await factory.get_domain_manager(
            session, controller.id, "network", "stats_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        await _maybe_set_site(cm, site_id)
        payload = await mgr.get_network_stats()
    return _stats_response(
        request, payload, "unifi_get_network_stats", limit=limit, cursor=cursor,
    )


@router.get(
    "/sites/{site_id}/stats/gateway",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_gateway_stats(
    request: Request,
    site_id: str,
    controller=Depends(resolve_controller),
    limit: int = Query(50, ge=1, le=500),
    cursor: str | None = Query(None),
) -> dict:
    require_capability(controller, "network")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    async with sm() as session:
        mgr = await factory.get_domain_manager(
            session, controller.id, "network", "stats_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        await _maybe_set_site(cm, site_id)
        payload = await mgr.get_gateway_stats()
    return _stats_response(
        request, payload, "unifi_get_gateway_stats", limit=limit, cursor=cursor,
    )


@router.get(
    "/sites/{site_id}/stats/dpi/site",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_site_dpi_traffic(
    request: Request,
    site_id: str,
    controller=Depends(resolve_controller),
    limit: int = Query(50, ge=1, le=500),
    cursor: str | None = Query(None),
) -> dict:
    require_capability(controller, "network")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    async with sm() as session:
        mgr = await factory.get_domain_manager(
            session, controller.id, "network", "stats_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        await _maybe_set_site(cm, site_id)
        payload = await mgr.get_site_dpi_traffic()
    return _stats_response(
        request, payload, "unifi_get_site_dpi_traffic", limit=limit, cursor=cursor,
    )


@router.get(
    "/sites/{site_id}/stats/dpi/clients/{mac}",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_client_dpi_traffic(
    request: Request,
    site_id: str,
    mac: str,
    controller=Depends(resolve_controller),
    limit: int = Query(50, ge=1, le=500),
    cursor: str | None = Query(None),
) -> dict:
    require_capability(controller, "network")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    async with sm() as session:
        mgr = await factory.get_domain_manager(
            session, controller.id, "network", "stats_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        await _maybe_set_site(cm, site_id)
        payload = await mgr.get_client_dpi_traffic(mac)
    return _stats_response(
        request, payload, "unifi_get_client_dpi_traffic", limit=limit, cursor=cursor,
    )


# ---------- DETAIL (currently mis-classified) — call dispatch-target methods ----------


@router.get(
    "/sites/{site_id}/stats/dpi",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_dpi_stats(
    request: Request,
    site_id: str,
    controller=Depends(resolve_controller),
    limit: int = Query(50, ge=1, le=500),
    cursor: str | None = Query(None),
) -> dict:
    """DETAIL kind currently; manager method is stats_manager.get_dpi_stats."""
    require_capability(controller, "network")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    async with sm() as session:
        mgr = await factory.get_domain_manager(
            session, controller.id, "network", "stats_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        await _maybe_set_site(cm, site_id)
        payload = await mgr.get_dpi_stats()
    return _stats_response(
        request, payload, "unifi_get_dpi_stats", limit=limit, cursor=cursor,
    )


@router.get(
    "/sites/{site_id}/stats/devices/{mac}",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_device_stats(
    request: Request,
    site_id: str,
    mac: str,
    controller=Depends(resolve_controller),
    limit: int = Query(50, ge=1, le=500),
    cursor: str | None = Query(None),
) -> dict:
    """DETAIL kind currently; dispatch routes to device_manager.get_device_details."""
    require_capability(controller, "network")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    try:
        async with sm() as session:
            mgr = await factory.get_domain_manager(
                session, controller.id, "network", "device_manager",
            )
            cm = await factory.get_connection_manager(session, controller.id, "network")
            await _maybe_set_site(cm, site_id)
            payload = await mgr.get_device_details(mac)
    except UniFiNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if payload is None:
        raise HTTPException(status_code=404, detail=f"device {mac} not found")
    return _stats_response(
        request, payload, "unifi_get_device_stats", limit=limit, cursor=cursor,
    )


@router.get(
    "/sites/{site_id}/stats/clients/{mac}",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_client_stats(
    request: Request,
    site_id: str,
    mac: str,
    controller=Depends(resolve_controller),
    limit: int = Query(50, ge=1, le=500),
    cursor: str | None = Query(None),
) -> dict:
    """DETAIL kind currently; dispatch routes to client_manager.get_client_details."""
    require_capability(controller, "network")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    try:
        async with sm() as session:
            mgr = await factory.get_domain_manager(
                session, controller.id, "network", "client_manager",
            )
            cm = await factory.get_connection_manager(session, controller.id, "network")
            await _maybe_set_site(cm, site_id)
            payload = await mgr.get_client_details(mac)
    except UniFiNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if payload is None:
        raise HTTPException(status_code=404, detail=f"client {mac} not found")
    return _stats_response(
        request, payload, "unifi_get_client_stats", limit=limit, cursor=cursor,
    )
