"""Bearer token auth middleware as a FastAPI dependency factory."""

from __future__ import annotations

from typing import Callable

from fastapi import HTTPException, Request, status
from sqlalchemy import select

from unifi_api.auth.api_key import verify_key
from unifi_api.auth.scopes import Scope, parse_scopes, scope_allows
from unifi_api.db.models import ApiKey


def require_scope(required: Scope) -> Callable:
    async def _dep(request: Request) -> ApiKey:
        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
        plaintext = auth_header[len("Bearer "):].strip()

        prefix = plaintext[:15]

        sm = request.app.state.sessionmaker
        async with sm() as session:
            row = (await session.execute(select(ApiKey).where(ApiKey.prefix == prefix))).scalar_one_or_none()
            if row is None or row.revoked_at is not None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unknown token")
            try:
                ok = verify_key(plaintext, row.hash)
            except ValueError:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="malformed token")
            if not ok:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

            held = parse_scopes(row.scopes)
            if not scope_allows(held, required):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient scope")
            return row

    return _dep
