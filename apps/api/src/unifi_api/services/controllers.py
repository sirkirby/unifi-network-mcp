"""Controller CRUD service. Encryption uses ColumnCipher on credentials_blob."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from unifi_api.db.crypto import ColumnCipher
from unifi_api.db.models import Controller


class ControllerNotFound(Exception):
    pass


@dataclass(frozen=True)
class CreateControllerPayload:
    name: str
    base_url: str
    username: str
    password: str
    api_token: str | None
    product_kinds: list[str]
    verify_tls: bool
    is_default: bool


def _serialize_creds(p: CreateControllerPayload) -> bytes:
    return json.dumps({
        "username": p.username,
        "password": p.password,
        "api_token": p.api_token,
    }).encode("utf-8")


async def _clear_default_flag(session: AsyncSession) -> None:
    await session.execute(sa_update(Controller).values(is_default=False))


async def create_controller(
    session: AsyncSession,
    cipher: ColumnCipher,
    payload: CreateControllerPayload,
) -> Controller:
    if payload.is_default:
        await _clear_default_flag(session)
    now = datetime.now(timezone.utc)
    row = Controller(
        id=str(uuid.uuid4()),
        name=payload.name,
        base_url=payload.base_url,
        product_kinds=",".join(payload.product_kinds),
        credentials_blob=cipher.encrypt(_serialize_creds(payload)),
        verify_tls=payload.verify_tls,
        is_default=payload.is_default,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    await session.flush()
    return row


async def list_controllers(session: AsyncSession) -> list[Controller]:
    result = await session.execute(select(Controller).order_by(Controller.created_at))
    return list(result.scalars().all())


async def get_controller(session: AsyncSession, controller_id: str) -> Controller:
    row = (await session.execute(
        select(Controller).where(Controller.id == controller_id)
    )).scalar_one_or_none()
    if row is None:
        raise ControllerNotFound(controller_id)
    return row


async def update_controller(
    session: AsyncSession,
    cipher: ColumnCipher,
    controller_id: str,
    *,
    name: str | None = None,
    base_url: str | None = None,
    product_kinds: list[str] | None = None,
    verify_tls: bool | None = None,
    is_default: bool | None = None,
    username: str | None = None,
    password: str | None = None,
    api_token: str | None = None,
) -> Controller:
    row = await get_controller(session, controller_id)
    if name is not None:
        row.name = name
    if base_url is not None:
        row.base_url = base_url
    if product_kinds is not None:
        row.product_kinds = ",".join(product_kinds)
    if verify_tls is not None:
        row.verify_tls = verify_tls
    if is_default is True:
        await _clear_default_flag(session)
        row.is_default = True
    elif is_default is False:
        row.is_default = False
    creds_changed = any(v is not None for v in (username, password, api_token))
    if creds_changed:
        existing = json.loads(cipher.decrypt(row.credentials_blob))
        if username is not None:
            existing["username"] = username
        if password is not None:
            existing["password"] = password
        if api_token is not None:
            existing["api_token"] = api_token
        row.credentials_blob = cipher.encrypt(json.dumps(existing).encode("utf-8"))
    row.updated_at = datetime.now(timezone.utc)
    await session.flush()
    return row


async def delete_controller(session: AsyncSession, controller_id: str) -> None:
    row = await get_controller(session, controller_id)
    await session.delete(row)
    await session.flush()
