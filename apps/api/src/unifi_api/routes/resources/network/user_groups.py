"""GET /v1/sites/{site_id}/user-groups[/{group_id}] — usergroups (QoS bandwidth profiles).

Phase 5A PR1 Cluster 2 — clients & user groups. Manager methods are
``UsergroupManager.get_usergroups`` (LIST) and ``get_usergroup_details``
(DETAIL); the route exposes the canonical ``/user-groups`` path.
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


def _group_key(obj) -> tuple:
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
    "/sites/{site_id}/user-groups",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def list_user_groups(
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
            session, controller.id, "network", "usergroup_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        if cm.site != site_id:
            await cm.set_site(site_id)
        all_groups = await mgr.get_usergroups()

    cursor_obj = _decode_cursor(cursor)
    page, next_cursor = paginate(
        list(all_groups), limit=limit, cursor=cursor_obj, key_fn=_group_key,
    )

    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("unifi_list_usergroups")
    items = [serializer.serialize(g) for g in page]
    hint = registry.render_hint_for_tool("unifi_list_usergroups")
    return {
        "items": items,
        "next_cursor": next_cursor.encode() if next_cursor else None,
        "render_hint": hint,
    }


@router.get(
    "/sites/{site_id}/user-groups/{group_id}",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_user_group_details(
    request: Request,
    site_id: str,
    group_id: str,
    controller=Depends(resolve_controller),
) -> dict:
    require_capability(controller, "network")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    async with sm() as session:
        mgr = await factory.get_domain_manager(
            session, controller.id, "network", "usergroup_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        if cm.site != site_id:
            await cm.set_site(site_id)
        group = await mgr.get_usergroup_details(group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="user group not found")

    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("unifi_get_usergroup_details")
    return {
        "data": serializer.serialize(group),
        "render_hint": registry.render_hint_for_tool("unifi_get_usergroup_details"),
    }
