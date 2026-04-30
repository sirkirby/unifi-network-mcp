"""GET /v1/sites/{site_id}/dpi-{applications,categories} — DPI lookups.

Phase 5A PR2 Cluster 4 — network filtering routes.

``DpiManager`` calls the official integration API and returns paginated
wrapper dicts: ``{"data": [...], "totalCount": int, "offset": int, "limit": int}``.
The route unwraps ``wrapper["data"]`` before paginating + serializing.

DPI category id ``0`` is real and falsy — pagination/sort handles it via
the ``or "" `` fallback only on missing keys, not on present-but-falsy values.
"""

from __future__ import annotations

from typing import Any, Iterable

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
    """Sort by id; treats `None` (missing) as `0` so present 0s order naturally."""
    raw = obj if isinstance(obj, dict) else getattr(obj, "raw", {}) or {}
    ident = raw.get("id")
    if ident is None:
        ident = raw.get("_id")
    if ident is None:
        ident = 0
    return (0, ident)


def _decode_cursor(cursor: str | None) -> Cursor | None:
    if not cursor:
        return None
    try:
        return Cursor.decode(cursor)
    except InvalidCursor:
        raise HTTPException(status_code=400, detail="invalid cursor")


def _unwrap(result: Any) -> list:
    """Extract bare list from a paginated DPI wrapper or pass through."""
    if isinstance(result, dict) and "data" in result:
        data = result.get("data") or []
        return list(data) if isinstance(data, Iterable) else []
    if isinstance(result, list):
        return result
    return []


@router.get(
    "/sites/{site_id}/dpi-applications",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def list_dpi_applications(
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
            session, controller.id, "network", "dpi_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        if cm.site != site_id:
            await cm.set_site(site_id)
        # Manager returns the integration-API wrapper. Ask for a wide page so
        # cursor-based pagination on the client side has the full set.
        result = await mgr.get_dpi_applications(limit=2500, offset=0)

    items_raw = _unwrap(result)
    cursor_obj = _decode_cursor(cursor)
    page, next_cursor = paginate(
        items_raw, limit=limit, cursor=cursor_obj, key_fn=_id_key,
    )
    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("unifi_list_dpi_applications")
    return {
        "items": [serializer.serialize(i) for i in page],
        "next_cursor": next_cursor.encode() if next_cursor else None,
        "render_hint": registry.render_hint_for_tool("unifi_list_dpi_applications"),
    }


@router.get(
    "/sites/{site_id}/dpi-categories",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def list_dpi_categories(
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
            session, controller.id, "network", "dpi_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        if cm.site != site_id:
            await cm.set_site(site_id)
        result = await mgr.get_dpi_categories(limit=500, offset=0)

    items_raw = _unwrap(result)
    cursor_obj = _decode_cursor(cursor)
    page, next_cursor = paginate(
        items_raw, limit=limit, cursor=cursor_obj, key_fn=_id_key,
    )
    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("unifi_list_dpi_categories")
    return {
        "items": [serializer.serialize(i) for i in page],
        "next_cursor": next_cursor.encode() if next_cursor else None,
        "render_hint": registry.render_hint_for_tool("unifi_list_dpi_categories"),
    }
