"""GET /v1/sites/{site_id}/clients[/{mac}] — network clients."""

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


def _client_key(obj) -> tuple:
    """Sort key on raw objects: (last_seen_int, mac) descending.

    We sort BEFORE serialization so we can use the integer last_seen
    epoch from the manager rather than the ISO string the serializer
    emits — integer compares are unambiguous, the ISO string isn't a
    safe sort key after the serializer transforms it.
    """
    raw = getattr(obj, "raw", obj if isinstance(obj, dict) else {})
    return (raw.get("last_seen") or 0, raw.get("mac") or "")


@router.get(
    "/sites/{site_id}/clients",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def list_clients(
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
            session, controller.id, "network", "client_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        if cm.site != site_id:
            await cm.set_site(site_id)
        all_clients = await mgr.get_clients()

    cursor_obj = None
    if cursor:
        try:
            cursor_obj = Cursor.decode(cursor)
        except InvalidCursor:
            raise HTTPException(status_code=400, detail="invalid cursor")

    page, next_cursor = paginate(
        list(all_clients), limit=limit, cursor=cursor_obj, key_fn=_client_key,
    )

    registry = request.app.state.serializer_registry
    entry = request.app.state.type_registry.lookup("network", "clients")
    if entry.kind == "type":
        items = [entry.payload.from_manager_output(c).to_dict() for c in page]
        hint = entry.payload.render_hint("list")
    else:
        items = [entry.payload.serialize(c) for c in page]
        hint = registry.render_hint_for_resource("network", "clients")

    return {
        "items": items,
        "next_cursor": next_cursor.encode() if next_cursor else None,
        "render_hint": hint,
    }


@router.get(
    "/sites/{site_id}/clients/{mac}",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_client(
    request: Request,
    site_id: str,
    mac: str,
    controller=Depends(resolve_controller),
) -> dict:
    require_capability(controller, "network")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    try:
        async with sm() as session:
            mgr = await factory.get_domain_manager(
                session, controller.id, "network", "client_manager",
            )
            cm = await factory.get_connection_manager(session, controller.id, "network")
            if cm.site != site_id:
                await cm.set_site(site_id)
            client = await mgr.get_client_details(mac)
    except UniFiNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")

    registry = request.app.state.serializer_registry
    entry = request.app.state.type_registry.lookup("network", "clients/{mac}")
    if entry.kind == "type":
        data = entry.payload.from_manager_output(client).to_dict()
        hint = entry.payload.render_hint("detail")
    else:
        data = entry.payload.serialize(client)
        hint = registry.render_hint_for_resource("network", "clients/{mac}")
    return {
        "data": data,
        "render_hint": hint,
    }
