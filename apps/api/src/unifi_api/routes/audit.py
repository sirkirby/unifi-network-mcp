"""Audit log query route — admin-scoped, paginated, filterable."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select

from unifi_api.auth.middleware import require_scope
from unifi_api.auth.scopes import Scope
from unifi_api.db.models import AuditLog
from unifi_api.services.pagination import Cursor, InvalidCursor, paginate


router = APIRouter()


def _row_to_dict(r: AuditLog) -> dict:
    return {
        "id": r.id,
        "ts": r.ts.isoformat(),
        "key_id_prefix": r.key_id_prefix,
        "controller": r.controller,
        "target": r.target,
        "outcome": r.outcome,
        "error_kind": r.error_kind,
        "detail": r.detail,
    }


def _audit_key(r: AuditLog) -> tuple:
    return (int(r.ts.timestamp() * 1000), str(r.id))


@router.get(
    "/audit",
    dependencies=[Depends(require_scope(Scope.ADMIN))],
)
async def list_audit(
    request: Request,
    controller: str | None = Query(None),
    outcome: str | None = Query(None),
    since: str | None = Query(None),
    until: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    cursor: str | None = Query(None),
) -> dict:
    sm = request.app.state.sessionmaker

    stmt = select(AuditLog)
    if controller is not None:
        stmt = stmt.where(AuditLog.controller == controller)
    if outcome is not None:
        stmt = stmt.where(AuditLog.outcome == outcome)
    if since is not None:
        try:
            stmt = stmt.where(AuditLog.ts >= datetime.fromisoformat(since))
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid 'since' timestamp")
    if until is not None:
        try:
            stmt = stmt.where(AuditLog.ts <= datetime.fromisoformat(until))
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid 'until' timestamp")
    if q is not None:
        stmt = stmt.where(AuditLog.target.ilike(f"%{q}%"))
    stmt = stmt.order_by(AuditLog.ts.desc())

    async with sm() as session:
        rows = (await session.execute(stmt)).scalars().all()

    cursor_obj = None
    if cursor:
        try:
            cursor_obj = Cursor.decode(cursor)
        except InvalidCursor:
            raise HTTPException(status_code=400, detail="invalid cursor")

    page, next_cursor = paginate(
        list(rows), limit=limit, cursor=cursor_obj, key_fn=_audit_key,
    )

    return {
        "items": [_row_to_dict(r) for r in page],
        "next_cursor": next_cursor.encode() if next_cursor else None,
    }
