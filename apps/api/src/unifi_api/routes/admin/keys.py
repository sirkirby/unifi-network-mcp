"""Admin UI routes for managing API keys (list / create / revoke).

The page itself, the create form, and the revoke action are admin-scoped.
Plaintext keys are emitted exactly once (in the create response) and never
re-shown; the listing returns prefixes only.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from sqlalchemy import select

from unifi_api.auth.api_key import ApiKeyEnv, generate_key, hash_key
from unifi_api.auth.middleware import require_scope
from unifi_api.auth.scopes import Scope
from unifi_api.db.models import ApiKey
from unifi_api.routes.admin._common import render


router = APIRouter()


async def _list_keys(sm) -> list[ApiKey]:
    async with sm() as session:
        return list(
            (await session.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))).scalars().all()
        )


@router.get(
    "/admin/keys",
    include_in_schema=False,
    dependencies=[Depends(require_scope(Scope.ADMIN))],
)
async def keys_page(request: Request):
    rows = await _list_keys(request.app.state.sessionmaker)
    return render(request, "keys/list.html", {"keys": rows})


@router.post(
    "/admin/keys/create",
    include_in_schema=False,
    dependencies=[Depends(require_scope(Scope.ADMIN))],
)
async def keys_create(
    request: Request,
    name: str = Form(...),
    scopes: str = Form("read"),
):
    """Generate a new API key and return the modal fragment containing the plaintext."""
    sm = request.app.state.sessionmaker
    material = generate_key(env=ApiKeyEnv.LIVE)
    async with sm() as session:
        session.add(
            ApiKey(
                id=str(uuid.uuid4()),
                prefix=material.prefix,
                hash=hash_key(material.plaintext),
                scopes=scopes,
                name=name,
                created_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()
    rows = await _list_keys(sm)
    return render(
        request,
        "keys/_created_modal.html",
        {
            "plaintext": material.plaintext,
            "name": name,
            "scopes": scopes,
            "keys": rows,  # for an updated table to refresh-swap into via hx-swap-oob
        },
    )


@router.post(
    "/admin/keys/{key_id}/revoke",
    include_in_schema=False,
    dependencies=[Depends(require_scope(Scope.ADMIN))],
)
async def keys_revoke(request: Request, key_id: str):
    sm = request.app.state.sessionmaker
    async with sm() as session:
        row = await session.get(ApiKey, key_id)
        if row is None:
            raise HTTPException(status_code=404, detail="key not found")
        if row.revoked_at is not None:
            # idempotent: already revoked, return empty so HTMX still removes the row
            return Response(status_code=200, content="", headers={"Cache-Control": "no-store"})
        row.revoked_at = datetime.now(timezone.utc)
        await session.commit()
    # Empty body — HTMX hx-swap="outerHTML" replaces the row with nothing.
    return Response(status_code=200, content="", headers={"Cache-Control": "no-store"})
