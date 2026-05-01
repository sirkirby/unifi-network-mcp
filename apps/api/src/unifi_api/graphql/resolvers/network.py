"""NetworkQuery — read-only GraphQL resolvers for the UniFi Network product.

Phase 6 PR2.5 Cluster A — adds DETAIL counterparts and remaining LIST
resolvers for the client / device / network type domains. Builds on the
foundation laid by Task 25a (PR2):

- Fetch helpers route through the request-scoped ``RequestCache`` so
  multi-resolver queries dedupe.
- Page wrappers carry pagination cursors per LIST resolver.
- DETAIL resolvers reuse the cached LIST snapshots where the manager
  exposes a snapshot method; per-id manager calls (``get_device_radio``,
  ``get_lldp_neighbors``, ``get_speedtest_status``) get their own keyed
  cache entries so distinct macs don't collide.

Cluster B+ (vpn/dns/routes/firewall/etc.) and relationship edges land in
follow-up dispatches.
"""

from __future__ import annotations

from typing import Any

import strawberry
from strawberry.types import Info

from unifi_api.graphql.context import GraphQLContext
from unifi_api.graphql.permissions import IsRead
from unifi_api.graphql.types.network.client import (
    BlockedClient,
    Client,
    ClientLookup,
)
from unifi_api.graphql.types.network.device import (
    AvailableChannel,
    Device,
    DeviceRadio,
    KnownRogueAp,
    LldpNeighbors,
    RfScanResult,
    RogueAp,
    SpeedtestStatus,
)
from unifi_api.graphql.types.network.network import Network
from unifi_api.graphql.types.network.system import NetworkHealth


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


async def _fetch_blocked_clients(
    ctx: GraphQLContext, controller: str, site: str,
) -> list:
    key = f"network/blocked-clients/{controller}/{site}"

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
            return list(await mgr.get_blocked_clients())

    return await ctx.cache.get_or_fetch(key, _do)


async def _fetch_client_by_ip(
    ctx: GraphQLContext, controller: str, site: str, ip: str,
) -> Any:
    key = f"network/client-by-ip/{controller}/{site}/{ip}"

    async def _do() -> Any:
        async with ctx.sessionmaker() as session:
            mgr = await ctx.manager_factory.get_domain_manager(
                session, controller, "network", "client_manager",
            )
            cm = await ctx.manager_factory.get_connection_manager(
                session, controller, "network",
            )
            if cm.site != site:
                await cm.set_site(site)
            return await mgr.get_client_by_ip(ip)

    return await ctx.cache.get_or_fetch(key, _do)


async def _fetch_device_radio(
    ctx: GraphQLContext, controller: str, site: str, mac: str,
) -> Any:
    key = f"network/device-radio/{controller}/{site}/{mac}"

    async def _do() -> Any:
        async with ctx.sessionmaker() as session:
            mgr = await ctx.manager_factory.get_domain_manager(
                session, controller, "network", "device_manager",
            )
            cm = await ctx.manager_factory.get_connection_manager(
                session, controller, "network",
            )
            if cm.site != site:
                await cm.set_site(site)
            return await mgr.get_device_radio(mac)

    return await ctx.cache.get_or_fetch(key, _do)


async def _fetch_lldp_neighbors(
    ctx: GraphQLContext, controller: str, site: str, device_mac: str,
) -> Any:
    key = f"network/lldp-neighbors/{controller}/{site}/{device_mac}"

    async def _do() -> Any:
        async with ctx.sessionmaker() as session:
            mgr = await ctx.manager_factory.get_domain_manager(
                session, controller, "network", "switch_manager",
            )
            cm = await ctx.manager_factory.get_connection_manager(
                session, controller, "network",
            )
            if cm.site != site:
                await cm.set_site(site)
            return await mgr.get_lldp_neighbors(device_mac)

    return await ctx.cache.get_or_fetch(key, _do)


async def _fetch_rogue_aps(
    ctx: GraphQLContext, controller: str, site: str, within_hours: int = 24,
) -> list:
    key = f"network/rogue-aps/{controller}/{site}/{within_hours}"

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
            return list(await mgr.list_rogue_aps(within_hours))

    return await ctx.cache.get_or_fetch(key, _do)


async def _fetch_known_rogue_aps(
    ctx: GraphQLContext, controller: str, site: str,
) -> list:
    key = f"network/known-rogue-aps/{controller}/{site}"

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
            return list(await mgr.list_known_rogue_aps())

    return await ctx.cache.get_or_fetch(key, _do)


async def _fetch_rf_scan_results(
    ctx: GraphQLContext, controller: str, site: str, ap_mac: str,
) -> list:
    key = f"network/rf-scan-results/{controller}/{site}/{ap_mac}"

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
            return list(await mgr.get_rf_scan_results(ap_mac) or [])

    return await ctx.cache.get_or_fetch(key, _do)


async def _fetch_available_channels(
    ctx: GraphQLContext, controller: str, site: str,
) -> list:
    key = f"network/available-channels/{controller}/{site}"

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
            return list(await mgr.list_available_channels() or [])

    return await ctx.cache.get_or_fetch(key, _do)


async def _fetch_speedtest_status(
    ctx: GraphQLContext, controller: str, site: str, gateway_mac: str,
) -> Any:
    key = f"network/speedtest-status/{controller}/{site}/{gateway_mac}"

    async def _do() -> Any:
        async with ctx.sessionmaker() as session:
            mgr = await ctx.manager_factory.get_domain_manager(
                session, controller, "network", "device_manager",
            )
            cm = await ctx.manager_factory.get_connection_manager(
                session, controller, "network",
            )
            if cm.site != site:
                await cm.set_site(site)
            return await mgr.get_speedtest_status(gateway_mac)

    return await ctx.cache.get_or_fetch(key, _do)


async def _fetch_network_health(
    ctx: GraphQLContext, controller: str, site: str,
) -> list:
    key = f"network/network-health/{controller}/{site}"

    async def _do() -> list:
        async with ctx.sessionmaker() as session:
            mgr = await ctx.manager_factory.get_domain_manager(
                session, controller, "network", "system_manager",
            )
            cm = await ctx.manager_factory.get_connection_manager(
                session, controller, "network",
            )
            if cm.site != site:
                await cm.set_site(site)
            return list(await mgr.get_network_health() or [])

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


@strawberry.type(description="Paginated page of blocked clients.")
class BlockedClientPage:
    items: list[BlockedClient]
    next_cursor: str | None


@strawberry.type(description="Paginated page of detected rogue APs.")
class RogueApPage:
    items: list[RogueAp]
    next_cursor: str | None


@strawberry.type(description="Paginated page of known (allowlisted) rogue APs.")
class KnownRogueApPage:
    items: list[KnownRogueAp]
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


def _blocked_key(c: Any) -> tuple:
    raw = _raw(c)
    if isinstance(raw, dict):
        ts = raw.get("last_seen")
        mac = raw.get("mac")
    else:
        ts = getattr(raw, "last_seen", None)
        mac = getattr(raw, "mac", None)
    return (int(ts or 0), str(mac or ""))


def _bssid_key(row: Any) -> tuple:
    raw = _raw(row)
    if isinstance(raw, dict):
        ts = raw.get("last_seen")
        bssid = raw.get("bssid")
    else:
        ts = getattr(raw, "last_seen", None)
        bssid = getattr(raw, "bssid", None)
    return (int(ts or 0), str(bssid or ""))


# ---------------------------------------------------------------------------
# NetworkQuery
# ---------------------------------------------------------------------------


def _decode_cursor(cursor: str | None):
    """Translate an opaque cursor string to a Cursor (or raise ValueError)."""
    from unifi_api.services.pagination import Cursor, InvalidCursor

    if not cursor:
        return None
    try:
        return Cursor.decode(cursor)
    except InvalidCursor:
        raise ValueError("invalid cursor")


@strawberry.type(description="Read-only access to UniFi Network resources.")
class NetworkQuery:
    # ---- Client domain ---------------------------------------------------

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

        from unifi_api.services.pagination import paginate

        cursor_obj = _decode_cursor(cursor)
        page, next_cursor = paginate(
            list(raw), limit=limit, cursor=cursor_obj, key_fn=_client_key,
        )
        return ClientPage(
            items=[Client.from_manager_output(c) for c in page],
            next_cursor=next_cursor.encode() if next_cursor else None,
        )

    @strawberry.field(
        permission_classes=[IsRead],
        description="Look up a single client by MAC address.",
    )
    async def client(
        self,
        info: Info,
        controller: strawberry.ID,
        mac: strawberry.ID,
        site: str = "default",
    ) -> Client | None:
        ctx: GraphQLContext = info.context
        raw = await _fetch_clients(ctx, controller, site)
        for c in raw:
            r = _raw(c)
            c_mac = r.get("mac") if isinstance(r, dict) else getattr(r, "mac", None)
            if c_mac == mac:
                return Client.from_manager_output(c)
        return None

    @strawberry.field(
        permission_classes=[IsRead],
        description="List clients currently blocked from the network (paginated).",
    )
    async def blocked_clients(
        self,
        info: Info,
        controller: strawberry.ID,
        site: str = "default",
        limit: int = 50,
        cursor: str | None = None,
    ) -> BlockedClientPage:
        ctx: GraphQLContext = info.context
        raw = await _fetch_blocked_clients(ctx, controller, site)

        from unifi_api.services.pagination import paginate

        cursor_obj = _decode_cursor(cursor)
        page, next_cursor = paginate(
            list(raw), limit=limit, cursor=cursor_obj, key_fn=_blocked_key,
        )
        return BlockedClientPage(
            items=[BlockedClient.from_manager_output(c) for c in page],
            next_cursor=next_cursor.encode() if next_cursor else None,
        )

    @strawberry.field(
        permission_classes=[IsRead],
        description="Look up a client by IP address (online-presence check).",
    )
    async def client_by_ip(
        self,
        info: Info,
        controller: strawberry.ID,
        ip: str,
        site: str = "default",
    ) -> ClientLookup | None:
        ctx: GraphQLContext = info.context
        raw = await _fetch_client_by_ip(ctx, controller, site, ip)
        if raw is None:
            return None
        return ClientLookup.from_manager_output(raw)

    # ---- Device domain ---------------------------------------------------

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

        from unifi_api.services.pagination import paginate

        cursor_obj = _decode_cursor(cursor)
        page, next_cursor = paginate(
            list(raw), limit=limit, cursor=cursor_obj, key_fn=_device_key,
        )
        return DevicePage(
            items=[Device.from_manager_output(d) for d in page],
            next_cursor=next_cursor.encode() if next_cursor else None,
        )

    @strawberry.field(
        permission_classes=[IsRead],
        description="Look up a single device by MAC address.",
    )
    async def device(
        self,
        info: Info,
        controller: strawberry.ID,
        mac: strawberry.ID,
        site: str = "default",
    ) -> Device | None:
        ctx: GraphQLContext = info.context
        raw = await _fetch_devices(ctx, controller, site)
        for d in raw:
            r = _raw(d)
            d_mac = r.get("mac") if isinstance(r, dict) else getattr(r, "mac", None)
            if d_mac == mac:
                return Device.from_manager_output(d)
        return None

    @strawberry.field(
        permission_classes=[IsRead],
        description="Get the radio configuration for a UniFi access point.",
    )
    async def device_radio(
        self,
        info: Info,
        controller: strawberry.ID,
        mac: strawberry.ID,
        site: str = "default",
    ) -> DeviceRadio | None:
        ctx: GraphQLContext = info.context
        raw = await _fetch_device_radio(ctx, controller, site, mac)
        if raw is None:
            return None
        return DeviceRadio.from_manager_output(raw)

    @strawberry.field(
        permission_classes=[IsRead],
        description="Get LLDP neighbors reported by a switch.",
    )
    async def lldp_neighbors(
        self,
        info: Info,
        controller: strawberry.ID,
        device_mac: strawberry.ID,
        site: str = "default",
    ) -> LldpNeighbors | None:
        ctx: GraphQLContext = info.context
        raw = await _fetch_lldp_neighbors(ctx, controller, site, device_mac)
        if raw is None:
            return None
        return LldpNeighbors.from_manager_output(raw)

    @strawberry.field(
        permission_classes=[IsRead],
        description="List rogue (unknown) APs detected within a window (paginated).",
    )
    async def rogue_aps(
        self,
        info: Info,
        controller: strawberry.ID,
        site: str = "default",
        within_hours: int = 24,
        limit: int = 50,
        cursor: str | None = None,
    ) -> RogueApPage:
        ctx: GraphQLContext = info.context
        raw = await _fetch_rogue_aps(ctx, controller, site, within_hours)

        from unifi_api.services.pagination import paginate

        cursor_obj = _decode_cursor(cursor)
        page, next_cursor = paginate(
            list(raw), limit=limit, cursor=cursor_obj, key_fn=_bssid_key,
        )
        return RogueApPage(
            items=[RogueAp.from_manager_output(r) for r in page],
            next_cursor=next_cursor.encode() if next_cursor else None,
        )

    @strawberry.field(
        permission_classes=[IsRead],
        description="List known (allowlisted) rogue APs (paginated).",
    )
    async def known_rogue_aps(
        self,
        info: Info,
        controller: strawberry.ID,
        site: str = "default",
        limit: int = 50,
        cursor: str | None = None,
    ) -> KnownRogueApPage:
        ctx: GraphQLContext = info.context
        raw = await _fetch_known_rogue_aps(ctx, controller, site)

        from unifi_api.services.pagination import paginate

        cursor_obj = _decode_cursor(cursor)
        page, next_cursor = paginate(
            list(raw), limit=limit, cursor=cursor_obj, key_fn=_bssid_key,
        )
        return KnownRogueApPage(
            items=[KnownRogueAp.from_manager_output(r) for r in page],
            next_cursor=next_cursor.encode() if next_cursor else None,
        )

    @strawberry.field(
        permission_classes=[IsRead],
        description="List RF-scan results for a specific access point.",
    )
    async def rf_scan_results(
        self,
        info: Info,
        controller: strawberry.ID,
        ap_mac: strawberry.ID,
        site: str = "default",
    ) -> list[RfScanResult]:
        ctx: GraphQLContext = info.context
        raw = await _fetch_rf_scan_results(ctx, controller, site, ap_mac)
        return [RfScanResult.from_manager_output(r) for r in raw]

    @strawberry.field(
        permission_classes=[IsRead],
        description="List wireless channels allowed by the regulatory domain.",
    )
    async def available_channels(
        self,
        info: Info,
        controller: strawberry.ID,
        site: str = "default",
    ) -> list[AvailableChannel]:
        ctx: GraphQLContext = info.context
        raw = await _fetch_available_channels(ctx, controller, site)
        return [AvailableChannel.from_manager_output(r) for r in raw]

    @strawberry.field(
        permission_classes=[IsRead],
        description="Get the gateway speedtest status (idle/running + last results).",
    )
    async def speedtest_status(
        self,
        info: Info,
        controller: strawberry.ID,
        gateway_mac: strawberry.ID,
        site: str = "default",
    ) -> SpeedtestStatus | None:
        ctx: GraphQLContext = info.context
        raw = await _fetch_speedtest_status(ctx, controller, site, gateway_mac)
        if raw is None:
            return None
        return SpeedtestStatus.from_manager_output(raw)

    # ---- Network domain --------------------------------------------------

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

        from unifi_api.services.pagination import paginate

        cursor_obj = _decode_cursor(cursor)
        page, next_cursor = paginate(
            list(raw), limit=limit, cursor=cursor_obj, key_fn=_network_key,
        )
        return NetworkPage(
            items=[Network.from_manager_output(n) for n in page],
            next_cursor=next_cursor.encode() if next_cursor else None,
        )

    @strawberry.field(
        permission_classes=[IsRead],
        description="Look up a single LAN/VLAN network by id. (Named "
        "``networkDetail`` because ``network`` is reserved for the namespace.)",
    )
    async def network_detail(
        self,
        info: Info,
        controller: strawberry.ID,
        id: strawberry.ID,
        site: str = "default",
    ) -> Network | None:
        ctx: GraphQLContext = info.context
        raw = await _fetch_networks(ctx, controller, site)
        for n in raw:
            r = _raw(n)
            if isinstance(r, dict):
                nid = r.get("_id") or r.get("id")
            else:
                nid = getattr(r, "_id", None) or getattr(r, "id", None)
            if nid == id:
                return Network.from_manager_output(n)
        return None

    @strawberry.field(
        permission_classes=[IsRead],
        description="Get the controller's network-health subsystems list.",
    )
    async def network_health(
        self,
        info: Info,
        controller: strawberry.ID,
        site: str = "default",
    ) -> list[NetworkHealth]:
        ctx: GraphQLContext = info.context
        raw = await _fetch_network_health(ctx, controller, site)
        return [NetworkHealth.from_manager_output(r) for r in raw]
