"""GET /v1/sites/{site_id}/cameras[/{camera_id}] — protect cameras.

Protect is a single-controller, no-site product: the protect connection
manager has no ``set_site`` method. We guard the call with ``getattr``
so the endpoint shape stays consistent with the network resources.
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


def _camera_key(obj) -> tuple:
    """Sort by (0, id) — id-stable order, no time component."""
    raw = obj if isinstance(obj, dict) else getattr(obj, "raw", {})
    return (0, raw.get("id") or "")


async def _maybe_set_site(cm, site_id: str) -> None:
    """Call cm.set_site(site_id) only if the CM exposes it.

    Protect's connection manager is single-controller-no-site and does not
    define set_site; network's does. Sharing the resource path means we
    accept ``site_id`` for URL symmetry but no-op on protect.
    """
    set_site = getattr(cm, "set_site", None)
    if set_site is None:
        return
    if getattr(cm, "site", None) != site_id:
        await set_site(site_id)


@router.get(
    "/sites/{site_id}/cameras",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def list_cameras(
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
            session, controller.id, "protect", "camera_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "protect")
        await _maybe_set_site(cm, site_id)
        all_cameras = await mgr.list_cameras()

    cursor_obj = None
    if cursor:
        try:
            cursor_obj = Cursor.decode(cursor)
        except InvalidCursor:
            raise HTTPException(status_code=400, detail="invalid cursor")

    page, next_cursor = paginate(
        list(all_cameras), limit=limit, cursor=cursor_obj, key_fn=_camera_key,
    )

    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_resource("protect", "cameras")
    items = [serializer.serialize(c) for c in page]
    hint = registry.render_hint_for_resource("protect", "cameras")

    return {
        "items": items,
        "next_cursor": next_cursor.encode() if next_cursor else None,
        "render_hint": hint,
    }


@router.get(
    "/sites/{site_id}/cameras/{camera_id}",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_camera(
    request: Request,
    site_id: str,
    camera_id: str,
    controller=Depends(resolve_controller),
) -> dict:
    require_capability(controller, "protect")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    async with sm() as session:
        mgr = await factory.get_domain_manager(
            session, controller.id, "protect", "camera_manager",
        )
        cm = await factory.get_connection_manager(session, controller.id, "protect")
        await _maybe_set_site(cm, site_id)
        try:
            camera = await mgr.get_camera(camera_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="camera not found")

    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_resource("protect", "cameras/{id}")
    return {
        "data": serializer.serialize(camera),
        "render_hint": registry.render_hint_for_resource("protect", "cameras/{id}"),
    }


# ---------------------------------------------------------------------------
# Per-camera nested reads (Phase 5A PR3 Cluster 1).
#
# Camera analytics/streams/snapshot are intentionally nested under
# /cameras/{id}/* — the spec's only flat-layout exception, since these
# resources are intrinsically per-camera. The serializers live alongside
# the LIST/DETAIL serializer in unifi_api.serializers.protect.cameras.
# ---------------------------------------------------------------------------


@router.get(
    "/sites/{site_id}/cameras/{camera_id}/analytics",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_camera_analytics(
    request: Request,
    site_id: str,
    camera_id: str,
    controller=Depends(resolve_controller),
) -> dict:
    require_capability(controller, "protect")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    try:
        async with sm() as session:
            mgr = await factory.get_domain_manager(
                session, controller.id, "protect", "camera_manager",
            )
            cm = await factory.get_connection_manager(session, controller.id, "protect")
            await _maybe_set_site(cm, site_id)
            analytics = await mgr.get_camera_analytics(camera_id)
    except UniFiNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if analytics is None:
        raise HTTPException(
            status_code=404, detail=f"camera analytics for {camera_id} not found",
        )

    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("protect_get_camera_analytics")
    return {
        "data": serializer.serialize(analytics),
        "render_hint": registry.render_hint_for_tool("protect_get_camera_analytics"),
    }


@router.get(
    "/sites/{site_id}/cameras/{camera_id}/streams",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_camera_streams(
    request: Request,
    site_id: str,
    camera_id: str,
    controller=Depends(resolve_controller),
) -> dict:
    require_capability(controller, "protect")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    try:
        async with sm() as session:
            mgr = await factory.get_domain_manager(
                session, controller.id, "protect", "camera_manager",
            )
            cm = await factory.get_connection_manager(session, controller.id, "protect")
            await _maybe_set_site(cm, site_id)
            streams = await mgr.get_camera_streams(camera_id)
    except UniFiNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if streams is None:
        raise HTTPException(
            status_code=404, detail=f"camera streams for {camera_id} not found",
        )

    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("protect_get_camera_streams")
    return {
        "data": serializer.serialize(streams),
        "render_hint": registry.render_hint_for_tool("protect_get_camera_streams"),
    }


@router.get(
    "/sites/{site_id}/cameras/{camera_id}/snapshot",
    dependencies=[Depends(require_scope(Scope.READ))],
)
async def get_camera_snapshot(
    request: Request,
    site_id: str,
    camera_id: str,
    controller=Depends(resolve_controller),
) -> dict:
    """Return snapshot metadata (size_bytes / content_type / captured_at).

    The manager returns raw JPEG bytes; the SnapshotSerializer surfaces
    metadata only. A future ``/snapshot/raw`` endpoint that returns the
    binary body is deferred to Phase 5B if a UI consumer needs it.
    """
    require_capability(controller, "protect")
    factory = request.app.state.manager_factory
    sm = request.app.state.sessionmaker
    try:
        async with sm() as session:
            mgr = await factory.get_domain_manager(
                session, controller.id, "protect", "camera_manager",
            )
            cm = await factory.get_connection_manager(session, controller.id, "protect")
            await _maybe_set_site(cm, site_id)
            snapshot = await mgr.get_snapshot(camera_id)
    except UniFiNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if snapshot is None:
        raise HTTPException(
            status_code=404, detail=f"snapshot for {camera_id} not found",
        )

    registry = request.app.state.serializer_registry
    serializer = registry.serializer_for_tool("protect_get_snapshot")
    return {
        "data": serializer.serialize(snapshot),
        "render_hint": registry.render_hint_for_tool("protect_get_snapshot"),
    }
