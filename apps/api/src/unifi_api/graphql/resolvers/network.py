"""NetworkQuery — read-only GraphQL resolvers for the UniFi Network product.

Phase 6 PR2 Task 25a — foundation only:
- Three fetch helpers (clients, devices, networks) routed through the
  request-scoped ``RequestCache`` so multi-resolver queries dedupe.
- Three Page wrappers (`ClientPage`, `DevicePage`, `NetworkPage`).
- ``NetworkQuery`` with the three resolvers (``clients``/``devices``/
  ``networks``). Subsequent dispatches add the remaining ~27 resolvers
  and relationship edges; this file establishes the canonical pattern.
"""

from __future__ import annotations

from typing import Any

import strawberry
from strawberry.types import Info

from unifi_api.graphql.context import GraphQLContext
from unifi_api.graphql.permissions import IsRead
from unifi_api.graphql.types.network.client import Client
from unifi_api.graphql.types.network.device import Device
from unifi_api.graphql.types.network.network import Network


# ---------------------------------------------------------------------------
# Fetch helpers — each goes through ctx.cache.get_or_fetch so concurrent
# resolvers in the same request share a single manager round-trip.
# ---------------------------------------------------------------------------


async def _fetch_clients(ctx: GraphQLContext, controller: str, site: str) -> list:
    key = f"network/clients/{controller}/{site}"

    async def _do() -> list:
        async with ctx.sessionmaker() as session:
            mgr = await ctx.manager_factory.get_domain_manager(
                session, controller, "network", "client_manager",
            )
            cm = await ctx.manager_factory.get_connection_manager(
                session, controller, "network",
            )
            if cm.site != site:
                await cm.set_site(site)
            return list(await mgr.get_clients())

    return await ctx.cache.get_or_fetch(key, _do)


async def _fetch_devices(ctx: GraphQLContext, controller: str, site: str) -> list:
    key = f"network/devices/{controller}/{site}"

    async def _do() -> list:
        async with ctx.sessionmaker() as session:
            mgr = await ctx.manager_factory.get_domain_manager(
                session, controller, "network", "device_manager",
            )
            cm = await ctx.manager_factory.get_connection_manager(
                session, controller, "network",
            )
            if cm.site != site:
                await cm.set_site(site)
            return list(await mgr.get_devices())

    return await ctx.cache.get_or_fetch(key, _do)


async def _fetch_networks(ctx: GraphQLContext, controller: str, site: str) -> list:
    key = f"network/networks/{controller}/{site}"

    async def _do() -> list:
        async with ctx.sessionmaker() as session:
            mgr = await ctx.manager_factory.get_domain_manager(
                session, controller, "network", "network_manager",
            )
            cm = await ctx.manager_factory.get_connection_manager(
                session, controller, "network",
            )
            if cm.site != site:
                await cm.set_site(site)
            return list(await mgr.get_networks())

    return await ctx.cache.get_or_fetch(key, _do)


# ---------------------------------------------------------------------------
# Page wrappers
# ---------------------------------------------------------------------------


@strawberry.type(description="Paginated page of clients.")
class ClientPage:
    items: list[Client]
    next_cursor: str | None


@strawberry.type(description="Paginated page of devices.")
class DevicePage:
    items: list[Device]
    next_cursor: str | None


@strawberry.type(description="Paginated page of network configurations.")
class NetworkPage:
    items: list[Network]
    next_cursor: str | None


# ---------------------------------------------------------------------------
# Key extractors — operate on raw manager outputs (objects or dicts).
# Each returns (timestamp_or_zero, secondary_id) for stable descending sort.
# ---------------------------------------------------------------------------


def _raw(obj: Any) -> Any:
    raw = getattr(obj, "raw", None)
    if isinstance(raw, dict):
        return raw
    if isinstance(obj, dict):
        return obj
    return obj


def _client_key(c: Any) -> tuple:
    raw = _raw(c)
    if isinstance(raw, dict):
        ts = raw.get("last_seen")
        mac = raw.get("mac")
    else:
        ts = getattr(raw, "last_seen", None)
        mac = getattr(raw, "mac", None)
    return (int(ts or 0), str(mac or ""))


def _device_key(d: Any) -> tuple:
    raw = _raw(d)
    if isinstance(raw, dict):
        mac = raw.get("mac")
        name = raw.get("name")
    else:
        mac = getattr(raw, "mac", None)
        name = getattr(raw, "name", None)
    # Devices have no natural timestamp; sort by name desc with mac as tiebreaker.
    # Use 0 for the ts slot so paginate's ordering remains deterministic.
    return (0, f"{name or ''}|{mac or ''}")


def _network_key(n: Any) -> tuple:
    raw = _raw(n)
    if isinstance(raw, dict):
        nid = raw.get("_id") or raw.get("id")
        name = raw.get("name")
    else:
        nid = getattr(raw, "_id", None) or getattr(raw, "id", None)
        name = getattr(raw, "name", None)
    return (0, f"{name or ''}|{nid or ''}")


# ---------------------------------------------------------------------------
# NetworkQuery
# ---------------------------------------------------------------------------


@strawberry.type(description="Read-only access to UniFi Network resources.")
class NetworkQuery:
    @strawberry.field(
        permission_classes=[IsRead],
        description="List clients on the given controller/site (paginated).",
    )
    async def clients(
        self,
        info: Info,
        controller: strawberry.ID,
        site: str = "default",
        limit: int = 50,
        cursor: str | None = None,
    ) -> ClientPage:
        ctx: GraphQLContext = info.context
        raw = await _fetch_clients(ctx, controller, site)

        from unifi_api.services.pagination import Cursor, InvalidCursor, paginate

        cursor_obj = None
        if cursor:
            try:
                cursor_obj = Cursor.decode(cursor)
            except InvalidCursor:
                raise ValueError("invalid cursor")

        page, next_cursor = paginate(
            list(raw), limit=limit, cursor=cursor_obj, key_fn=_client_key,
        )
        return ClientPage(
            items=[Client.from_manager_output(c) for c in page],
            next_cursor=next_cursor.encode() if next_cursor else None,
        )

    @strawberry.field(
        permission_classes=[IsRead],
        description="List devices on the given controller/site (paginated).",
    )
    async def devices(
        self,
        info: Info,
        controller: strawberry.ID,
        site: str = "default",
        limit: int = 50,
        cursor: str | None = None,
    ) -> DevicePage:
        ctx: GraphQLContext = info.context
        raw = await _fetch_devices(ctx, controller, site)

        from unifi_api.services.pagination import Cursor, InvalidCursor, paginate

        cursor_obj = None
        if cursor:
            try:
                cursor_obj = Cursor.decode(cursor)
            except InvalidCursor:
                raise ValueError("invalid cursor")

        page, next_cursor = paginate(
            list(raw), limit=limit, cursor=cursor_obj, key_fn=_device_key,
        )
        return DevicePage(
            items=[Device.from_manager_output(d) for d in page],
            next_cursor=next_cursor.encode() if next_cursor else None,
        )

    @strawberry.field(
        permission_classes=[IsRead],
        description="List configured LAN/VLAN networks on the given controller/site (paginated).",
    )
    async def networks(
        self,
        info: Info,
        controller: strawberry.ID,
        site: str = "default",
        limit: int = 50,
        cursor: str | None = None,
    ) -> NetworkPage:
        ctx: GraphQLContext = info.context
        raw = await _fetch_networks(ctx, controller, site)

        from unifi_api.services.pagination import Cursor, InvalidCursor, paginate

        cursor_obj = None
        if cursor:
            try:
                cursor_obj = Cursor.decode(cursor)
            except InvalidCursor:
                raise ValueError("invalid cursor")

        page, next_cursor = paginate(
            list(raw), limit=limit, cursor=cursor_obj, key_fn=_network_key,
        )
        return NetworkPage(
            items=[Network.from_manager_output(n) for n in page],
            next_cursor=next_cursor.encode() if next_cursor else None,
        )
