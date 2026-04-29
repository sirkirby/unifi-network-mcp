"""Bearer token auth middleware as a FastAPI dependency factory.

`_authenticate` resolves a bearer token to an ApiKey row (or raises 401).
`require_scope(scope)` returns a FastAPI dependency that authenticates and
then enforces the requested scope (raises 403 on insufficient scope).
"""

from __future__ import annotations

from typing import Callable

from fastapi import HTTPException, Request, status
from sqlalchemy import select

from unifi_api.auth.api_key import KEY_PATTERN, KEY_PREFIX_LEN, verify_key
from unifi_api.auth.scopes import Scope, parse_scopes, scope_allows
from unifi_api.db.models import ApiKey


async def _authenticate(request: Request) -> ApiKey:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    plaintext = auth_header[len("Bearer "):].strip()

    if not KEY_PATTERN.fullmatch(plaintext):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="malformed token")

    prefix = plaintext[:KEY_PREFIX_LEN]
    sm = request.app.state.sessionmaker
    async with sm() as session:
        row = (await session.execute(select(ApiKey).where(ApiKey.prefix == prefix))).scalar_one_or_none()
        if row is None or row.revoked_at is not None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unknown token")
        if not verify_key(plaintext, row.hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
        return row


def require_scope(required: Scope) -> Callable:
    async def _dep(request: Request) -> ApiKey:
        api_key = await _authenticate(request)
        held = parse_scopes(api_key.scopes)
        if not scope_allows(held, required):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient scope")
        return api_key

    return _dep
