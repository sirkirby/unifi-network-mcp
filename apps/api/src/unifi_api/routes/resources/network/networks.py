"""GET /v1/sites/{site_id}/networks[/{network_id}] — LAN/VLAN definitions."""

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


def _network_key(obj) -> tuple:
    """Sort by (0, id) — id-stable order, no time component."""
    raw = getattr(obj, "raw", obj if isinstance(obj, dict) else {})
    return (0, raw.get("_id") or raw.get("id") or "")


@router.get(
    "/sites/{site_id}/networks",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def list_networks(
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
            session, controller.id, "network", "network_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        if cm.site != site_id:
            await cm.set_site(site_id)
        all_networks = await mgr.get_networks()

    cursor_obj = None
    if cursor:
        try:
            cursor_obj = Cursor.decode(cursor)
        except InvalidCursor:
            raise HTTPException(status_code=400, detail="invalid cursor")

    page, next_cursor = paginate(
        list(all_networks), limit=limit, cursor=cursor_obj, key_fn=_network_key,
    )

    registry = request.app.state.serializer_registry
    entry = request.app.state.type_registry.lookup("network", "networks")
    if entry.kind == "type":
        items = [entry.payload.from_manager_output(n).to_dict() for n in page]
        hint = entry.payload.render_hint("list")
    else:
        items = [entry.payload.serialize(n) for n in page]
        hint = registry.render_hint_for_resource("network", "networks")

    return {
        "items": items,
        "next_cursor": next_cursor.encode() if next_cursor else None,
        "render_hint": hint,
    }


@router.get(
    "/sites/{site_id}/networks/{network_id}",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_network(
    request: Request,
    site_id: str,
    network_id: str,
    controller=Depends(resolve_controller),
) -> dict:
    require_capability(controller, "network")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    try:
        async with sm() as session:
            mgr = await factory.get_domain_manager(
                session, controller.id, "network", "network_manager",
            )
            cm = await factory.get_connection_manager(session, controller.id, "network")
            if cm.site != site_id:
                await cm.set_site(site_id)
            network = await mgr.get_network_details(network_id)
    except UniFiNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if network is None:
        raise HTTPException(status_code=404, detail="network not found")

    registry = request.app.state.serializer_registry
    entry = request.app.state.type_registry.lookup("network", "networks/{id}")
    if entry.kind == "type":
        data = entry.payload.from_manager_output(network).to_dict()
        hint = entry.payload.render_hint("detail")
    else:
        data = entry.payload.serialize(network)
        hint = registry.render_hint_for_resource("network", "networks/{id}")
    return {
        "data": data,
        "render_hint": hint,
    }
