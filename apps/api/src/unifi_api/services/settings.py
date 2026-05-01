"""Typed accessors over the app_settings key/value table."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from unifi_api.db.models import AppSetting

_SENTINEL: Any = object()


class UnknownSettingKey(KeyError):
    """Raised when a setting key is missing AND no default was provided."""


class SettingsService:
    """Async UPSERT-based key/value access to the app_settings table.

    All ``get_*``/``set_*`` methods are async — they open a session per call so
    the service can be held on ``app.state`` without dragging an open session
    around with it.
    """

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def get_str(self, key: str, default: Any = _SENTINEL) -> str:
        async with self._sm() as session:
            row = await session.get(AppSetting, key)
        if row is not None:
            return row.value
        if default is _SENTINEL:
            raise UnknownSettingKey(key)
        return default

    async def get_int(self, key: str, default: Any = _SENTINEL) -> int:
        try:
            return int(await self.get_str(key))
        except UnknownSettingKey:
            if default is _SENTINEL:
                raise
            return default

    async def get_bool(self, key: str, default: Any = _SENTINEL) -> bool:
        try:
            raw = await self.get_str(key)
        except UnknownSettingKey:
            if default is _SENTINEL:
                raise
            return default
        return raw.lower() in ("true", "1", "yes")

    async def set_str(self, key: str, value: str) -> None:
        async with self._sm() as session:
            row = await session.get(AppSetting, key)
            if row is None:
                session.add(
                    AppSetting(
                        key=key,
                        value=value,
                        updated_at=datetime.now(timezone.utc),
                    )
                )
            else:
                row.value = value
                row.updated_at = datetime.now(timezone.utc)
            await session.commit()

    async def set_int(self, key: str, value: int) -> None:
        await self.set_str(key, str(value))

    async def set_bool(self, key: str, value: bool) -> None:
        await self.set_str(key, "true" if value else "false")

    async def get_all(self) -> dict[str, str]:
        async with self._sm() as session:
            rows = (await session.execute(select(AppSetting))).scalars().all()
        return {r.key: r.value for r in rows}
