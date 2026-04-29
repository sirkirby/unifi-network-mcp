"""GET /v1/sites/{site_id}/devices[/{mac}] — network devices (UniFi APs/switches/gateways)."""

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


def _device_key(obj) -> tuple:
    """Sort by (uptime, mac) descending — most-recently-up devices first."""
    raw = getattr(obj, "raw", obj if isinstance(obj, dict) else {})
    return (raw.get("uptime") or 0, raw.get("mac") or "")


@router.get(
    "/sites/{site_id}/devices",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def list_devices(
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
            session, controller.id, "network", "device_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        if cm.site != site_id:
            await cm.set_site(site_id)
        all_devices = await mgr.get_devices()

    cursor_obj = None
    if cursor:
        try:
            cursor_obj = Cursor.decode(cursor)
        except InvalidCursor:
            raise HTTPException(status_code=400, detail="invalid cursor")

    page, next_cursor = paginate(
        list(all_devices), limit=limit, cursor=cursor_obj, key_fn=_device_key,
    )

    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_resource("network", "devices")
    items = [serializer.serialize(d) for d in page]
    hint = registry.render_hint_for_resource("network", "devices")

    return {
        "items": items,
        "next_cursor": next_cursor.encode() if next_cursor else None,
        "render_hint": hint,
    }


@router.get(
    "/sites/{site_id}/devices/{mac}",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_device(
    request: Request,
    site_id: str,
    mac: str,
    controller=Depends(resolve_controller),
) -> dict:
    require_capability(controller, "network")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    async with sm() as session:
        mgr = await factory.get_domain_manager(
            session, controller.id, "network", "device_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "network")
        if cm.site != site_id:
            await cm.set_site(site_id)
        device = await mgr.get_device_details(mac)
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")

    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_resource("network", "devices/{mac}")
    return {
        "data": serializer.serialize(device),
        "render_hint": registry.render_hint_for_resource("network", "devices/{mac}"),
    }
