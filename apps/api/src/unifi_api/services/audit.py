"""Audit log writer.

Synchronous insert in the request transaction. Failures of the audit insert
itself propagate to the caller (we don't silently drop audit records).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from unifi_api.db.models import AuditLog


async def write_audit(
    session: AsyncSession,
    *,
    key_id_prefix: str,
    controller: str | None,
    target: str,
    outcome: str,
    error_kind: str | None = None,
    detail: str | None = None,
) -> None:
    session.add(AuditLog(
        ts=datetime.now(timezone.utc),
        key_id_prefix=key_id_prefix,
        controller=controller,
        target=target,
        outcome=outcome,
        error_kind=error_kind,
        detail=detail,
    ))
    await session.flush()
