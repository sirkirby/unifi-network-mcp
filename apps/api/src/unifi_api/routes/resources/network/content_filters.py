"""GET /v1/sites/{site_id}/content-filters[/{filter_id}] — content filters.

Phase 5A PR2 Cluster 4 — network filtering routes.
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


@router.get(
    "/sites/{site_id}/content-filters",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def list_content_filters(
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
            session, controller.id, "network", "content_filter_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        if cm.site != site_id:
            await cm.set_site(site_id)
        items = await mgr.get_content_filters()

    cursor_obj = _decode_cursor(cursor)
    page, next_cursor = paginate(
        list(items), limit=limit, cursor=cursor_obj, key_fn=_id_key,
    )
    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("unifi_list_content_filters")
    return {
        "items": [serializer.serialize(i) for i in page],
        "next_cursor": next_cursor.encode() if next_cursor else None,
        "render_hint": registry.render_hint_for_tool("unifi_list_content_filters"),
    }


@router.get(
    "/sites/{site_id}/content-filters/{filter_id}",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_content_filter_details(
    request: Request,
    site_id: str,
    filter_id: str,
    controller=Depends(resolve_controller),
) -> dict:
    require_capability(controller, "network")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    try:
        async with sm() as session:
            mgr = await factory.get_domain_manager(
                session, controller.id, "network", "content_filter_manager",
            )
            cm = await factory.get_connection_manager(session, controller.id, "network")
            if cm.site != site_id:
                await cm.set_site(site_id)
            item = await mgr.get_content_filter_by_id(filter_id)
    except UniFiNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if item is None:
        raise HTTPException(
            status_code=404, detail=f"content filter {filter_id} not found",
        )
    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("unifi_get_content_filter_details")
    return {
        "data": serializer.serialize(item),
        "render_hint": registry.render_hint_for_tool("unifi_get_content_filter_details"),
    }
