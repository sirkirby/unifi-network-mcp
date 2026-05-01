"""Per-request, in-process cache + Info.context shape for GraphQL resolvers.

The RequestCache lives for one HTTP request only — it dedupes manager calls
within a single GraphQL query. No persistence, no cross-request sharing.
Resolvers reaching the same snapshot share one fetch.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from unifi_api.services.managers import ManagerFactory


class RequestCache:
    """Memoizes async fetches by key for the lifetime of one request.

    Concurrency-safe: two coroutines requesting the same key share a single
    in-flight Future, so concurrent resolvers don't double-fetch.
    """

    def __init__(self) -> None:
        self._values: dict[str, Any] = {}
        self._inflight: dict[str, asyncio.Future] = {}

    async def get_or_fetch(
        self, key: str, fetch: Callable[[], Awaitable[Any]]
    ) -> Any:
        if key in self._values:
            return self._values[key]
        if key in self._inflight:
            return await self._inflight[key]
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self._inflight[key] = fut
        try:
            value = await fetch()
            self._values[key] = value
            fut.set_result(value)
            return value
        except Exception as exc:
            fut.set_exception(exc)
            raise
        finally:
            self._inflight.pop(key, None)


@dataclass
class GraphQLContext:
    """Shape attached to Strawberry's Info.context for every resolver call."""

    cache: RequestCache = field(default_factory=RequestCache)
    sessionmaker: "async_sessionmaker[AsyncSession] | None" = None
    manager_factory: "ManagerFactory | None" = None
    api_key_id: str | None = None
    api_key_scopes: str | None = None
    api_key_prefix: str | None = None
