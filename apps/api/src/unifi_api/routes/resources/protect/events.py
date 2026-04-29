"""GET /v1/sites/{site_id}/events — protect event log.

LIST only (EVENT_LOG render kind). The protect manifest does not expose
a ``protect_get_event`` tool, so we don't expose a detail endpoint.
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


def _event_key(obj) -> tuple:
    """Sort by (start, id) descending — most recent first.

    EventManager.list_events already sorts desc server-side, but we
    re-sort here so paginate() can drive a stable cursor regardless of
    upstream ordering. The pagination helper sorts ascending, then the
    manifest's ``sort_default = "start:desc"`` reflects the intended
    user-facing direction.
    """
    raw = obj if isinstance(obj, dict) else getattr(obj, "raw", {})
    return (raw.get("start") or 0, raw.get("id") or "")


async def _maybe_set_site(cm, site_id: str) -> None:
    set_site = getattr(cm, "set_site", None)
    if set_site is None:
        return
    if getattr(cm, "site", None) != site_id:
        await set_site(site_id)


@router.get(
    "/sites/{site_id}/events",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def list_events(
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
            session, controller.id, "protect", "event_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "protect")
        await _maybe_set_site(cm, site_id)
        all_events = await mgr.list_events(limit=max(limit, 100))

    cursor_obj = None
    if cursor:
        try:
            cursor_obj = Cursor.decode(cursor)
        except InvalidCursor:
            raise HTTPException(status_code=400, detail="invalid cursor")

    page, next_cursor = paginate(
        list(all_events), limit=limit, cursor=cursor_obj, key_fn=_event_key,
    )

    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_resource("protect", "events")
    items = [serializer.serialize(e) for e in page]
    hint = registry.render_hint_for_resource("protect", "events")

    return {
        "items": items,
        "next_cursor": next_cursor.encode() if next_cursor else None,
        "render_hint": hint,
    }
