"""GET /v1/sites/{site_id}/chimes — protect chimes.

The protect ``ChimeManager`` exposes ``list_chimes``; there is no dedicated
``protect_get_chime`` tool in the manifest, so this module only ships LIST
(mirrors network firewall_zones, which is also LIST-only).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from unifi_api.auth.middleware import require_scope
from unifi_api.auth.scopes import Scope
from unifi_api.routes.resources._common import (
    require_capability,
    resolve_controller,
)
from unifi_api.routes.resources.protect.cameras import _maybe_set_site
from unifi_api.services.pagination import Cursor, InvalidCursor, paginate


router = APIRouter()


def _id_key(obj) -> tuple:
    raw = obj if isinstance(obj, dict) else getattr(obj, "raw", {}) or {}
    return (0, raw.get("id") or "")


def _decode_cursor(cursor: str | None) -> Cursor | None:
    if not cursor:
        return None
    try:
        return Cursor.decode(cursor)
    except InvalidCursor:
        raise HTTPException(status_code=400, detail="invalid cursor")


@router.get(
    "/sites/{site_id}/chimes",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def list_chimes(
    request: Request,
    site_id: str,
    controller=Depends(resolve_controller),
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None),
) -> dict:
    require_capability(controller, "protect")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    async with sm() as session:
        mgr = await factory.get_domain_manager(
            session, controller.id, "protect", "chime_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "protect")
        await _maybe_set_site(cm, site_id)
        items = await mgr.list_chimes()

    cursor_obj = _decode_cursor(cursor)
    page, next_cursor = paginate(
        list(items), limit=limit, cursor=cursor_obj, key_fn=_id_key,
    )
    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("protect_list_chimes")
    return {
        "items": [serializer.serialize(i) for i in page],
        "next_cursor": next_cursor.encode() if next_cursor else None,
        "render_hint": registry.render_hint_for_tool("protect_list_chimes"),
    }
