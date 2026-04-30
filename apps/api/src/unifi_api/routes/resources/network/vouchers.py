"""GET /v1/sites/{site_id}/vouchers and /voucher-details/{voucher_id} — hotspot.

Phase 5A PR2 Cluster 5. The detail endpoint uses a deliberately separate
path (``/voucher-details/{voucher_id}``) — both spec §5 and the underlying
``HotspotManager.get_voucher_details(voucher_id)`` key on the voucher's
internal ``_id``. The path param is named ``voucher_id`` to reflect what
the manager actually accepts.
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


def _voucher_key(obj) -> tuple:
    raw = obj if isinstance(obj, dict) else getattr(obj, "raw", {}) or {}
    return (raw.get("create_time") or 0, raw.get("_id") or raw.get("code") or "")


def _decode_cursor(cursor: str | None) -> Cursor | None:
    if not cursor:
        return None
    try:
        return Cursor.decode(cursor)
    except InvalidCursor:
        raise HTTPException(status_code=400, detail="invalid cursor")


@router.get(
    "/sites/{site_id}/vouchers",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def list_vouchers(
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
            session, controller.id, "network", "hotspot_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        if cm.site != site_id:
            await cm.set_site(site_id)
        items = await mgr.get_vouchers()

    cursor_obj = _decode_cursor(cursor)
    page, next_cursor = paginate(
        list(items), limit=limit, cursor=cursor_obj, key_fn=_voucher_key,
    )
    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("unifi_list_vouchers")
    return {
        "items": [serializer.serialize(i) for i in page],
        "next_cursor": next_cursor.encode() if next_cursor else None,
        "render_hint": registry.render_hint_for_tool("unifi_list_vouchers"),
    }


@router.get(
    "/sites/{site_id}/voucher-details/{voucher_id}",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_voucher_details(
    request: Request,
    site_id: str,
    voucher_id: str,
    controller=Depends(resolve_controller),
) -> dict:
    require_capability(controller, "network")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    try:
        async with sm() as session:
            mgr = await factory.get_domain_manager(
                session, controller.id, "network", "hotspot_manager",
            )
            cm = await factory.get_connection_manager(session, controller.id, "network")
            if cm.site != site_id:
                await cm.set_site(site_id)
            voucher = await mgr.get_voucher_details(voucher_id)
    except UniFiNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if voucher is None:
        raise HTTPException(
            status_code=404, detail=f"voucher {voucher_id} not found",
        )
    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("unifi_get_voucher_details")
    return {
        "data": serializer.serialize(voucher),
        "render_hint": registry.render_hint_for_tool("unifi_get_voucher_details"),
    }
