"""FastAPI app factory."""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from starlette.middleware.cors import CORSMiddleware

from unifi_api.auth.cache import ArgonVerifyCache
from unifi_api.config import ApiConfig
from unifi_api.db.crypto import ColumnCipher, derive_key
from unifi_api.db.engine import create_engine
from unifi_api.db.session import get_sessionmaker
from unifi_api.logging import request_id_ctx
from unifi_api.routes import actions as actions_routes
from unifi_api.routes import audit as audit_routes
from unifi_api.routes import catalog as catalog_routes
from unifi_api.routes import controllers as controllers_routes
from unifi_api.routes import health
from unifi_api.routes.resources.network import (
    acl as net_acl_routes,
    ap_groups as net_ap_groups_routes,
    blocked_clients as net_blocked_clients_routes,
    client_groups as net_client_groups_routes,
    clients as net_clients_routes,
    content_filters as net_content_filters_routes,
    devices as net_devices_routes,
    dns as net_dns_routes,
    dpi as net_dpi_routes,
    events as net_events_routes,
    firewall_groups as net_firewall_groups_routes,
    firewall_rules as net_firewall_routes,
    firewall_zones as net_firewall_zones_routes,
    lldp as net_lldp_routes,
    lookup as net_lookup_routes,
    networks as net_networks_routes,
    oon as net_oon_routes,
    port_forwards as net_port_forwards_routes,
    qos as net_qos_routes,
    rogue_aps as net_rogue_aps_routes,
    routes as net_routes_routes,
    snmp as net_snmp_routes,
    speedtest as net_speedtest_routes,
    stats as net_stats_routes,
    switch as net_switch_routes,
    system as net_system_routes,
    user_groups as net_user_groups_routes,
    vouchers as net_vouchers_routes,
    vpn as net_vpn_routes,
    wireless as net_wireless_routes,
    wlans as net_wlans_routes,
)
from unifi_api.routes.resources.protect import (
    cameras as protect_cameras_routes,
    chimes as protect_chimes_routes,
    events as protect_events_routes,
    lights as protect_lights_routes,
    liveviews as protect_liveviews_routes,
    recordings as protect_recordings_routes,
    sensors as protect_sensors_routes,
    system as protect_system_routes,
)
from unifi_api.routes.resources.access import (
    credentials as access_credentials_routes,
    devices as access_devices_routes,
    doors as access_doors_routes,
    events as access_events_routes,
    policies as access_policies_routes,
    schedules as access_schedules_routes,
    system as access_system_routes,
    users as access_users_routes,
    visitors as access_visitors_routes,
)
from unifi_api.routes.streams import (
    access as access_streams_routes,
    access_per_door as access_per_door_routes,
    network as net_streams_routes,
    network_per_device as net_per_device_routes,
    protect as protect_streams_routes,
    protect_per_camera as protect_per_camera_routes,
)
from unifi_api.serializers._registry import discover_serializers
from unifi_api.services.capability_cache import CapabilityCache
from unifi_api.services.controllers import list_controllers
from unifi_api.services.managers import ManagerFactory
from unifi_api.services.manifest import ManifestRegistry
from unifi_api.services.streams import SubscriberPool


_streams_log = logging.getLogger("unifi-api.streams")


def create_app(config: ApiConfig) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup — manifest registry is loaded eagerly in create_app so it's
        # available even when the lifespan isn't run (e.g. ASGITransport tests).
        # Loading is idempotent and fast (file reads), so re-loading here keeps
        # the lifespan as the canonical startup hook.
        app.state.manifest_registry = ManifestRegistry.load_from_apps()

        # Phase 4B: eagerly start event listening for every (controller, product)
        # pair so SSE subscribers see a warm buffer on first connect. Failures
        # are logged warnings; they don't block startup. The stream endpoint for
        # a failed controller serves an empty buffer + tail of nothing.
        sm = app.state.sessionmaker
        try:
            async with sm() as session:
                controllers = await list_controllers(session)
        except Exception:
            controllers = []
            _streams_log.warning(
                "could not list controllers for eager start_listening", exc_info=True,
            )
        for controller in controllers:
            for product in [p for p in controller.product_kinds.split(",") if p]:
                try:
                    async with sm() as session:
                        mgr = await app.state.manager_factory.get_domain_manager(
                            session, controller.id, product, "event_manager",
                        )
                    if hasattr(mgr, "start_listening"):
                        await mgr.start_listening()
                        _streams_log.info(
                            "[streams] start_listening ok for %s/%s",
                            controller.id, product,
                        )
                except Exception:
                    _streams_log.warning(
                        "[streams] start_listening failed for %s/%s",
                        controller.id, product, exc_info=True,
                    )

        yield
        # Shutdown — drop manager caches first, then engine
        factory = app.state.manager_factory
        cached_ids = list({k[0] for k in factory._connection_cache.keys()})
        for cid in cached_ids:
            await factory.invalidate_controller(cid)
        await app.state.engine.dispose()

    app = FastAPI(
        title="unifi-api",
        version="0.1.0",
        openapi_url="/v1/openapi.json",
        docs_url="/v1/docs",
        lifespan=lifespan,
    )

    if config.http.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(config.http.cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        token = request_id_ctx.set(rid)
        try:
            response: Response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            request_id_ctx.reset(token)

    # Wire DB
    # Validate the encryption key exists at startup; service refuses to start without it.
    db_key = ApiConfig.read_db_key()
    engine = create_engine(config.db.path)
    app.state.engine = engine
    app.state.sessionmaker = get_sessionmaker(engine)

    cipher = ColumnCipher(derive_key(db_key))
    app.state.cipher = cipher
    app.state.manager_factory = ManagerFactory(app.state.sessionmaker, cipher)
    app.state.subscriber_pool = SubscriberPool()
    app.state.argon_cache = ArgonVerifyCache()
    app.state.capability_cache = CapabilityCache()
    app.state.manifest_registry = ManifestRegistry.load_from_apps()
    # Discover and register every serializer module, then validate against the
    # full manifest. Phase 4A landed coverage for all 235 manifest tools, so
    # strict mode is now the runtime contract: any tool added to the manifest
    # without a registered serializer raises SerializerRegistryError at lifespan
    # startup. The CI gate test_every_tool_has_a_serializer enforces the same
    # invariant in apps/api/tests/.
    manifest_tool_names = set(app.state.manifest_registry.all_tools())
    app.state.serializer_registry = discover_serializers(manifest_tool_names)

    app.include_router(health.router, prefix="/v1")
    app.include_router(controllers_routes.router, prefix="/v1")
    app.include_router(actions_routes.router, prefix="/v1")
    app.include_router(catalog_routes.router, prefix="/v1")
    app.include_router(audit_routes.router, prefix="/v1")
    for r in (
        net_clients_routes,
        net_devices_routes,
        net_networks_routes,
        net_firewall_routes,
        net_wlans_routes,
        net_switch_routes,
        net_lldp_routes,
        net_rogue_aps_routes,
        net_wireless_routes,
        net_speedtest_routes,
        net_blocked_clients_routes,
        net_client_groups_routes,
        net_user_groups_routes,
        net_lookup_routes,
        net_routes_routes,
        net_dns_routes,
        net_vpn_routes,
        net_ap_groups_routes,
        net_firewall_groups_routes,
        net_firewall_zones_routes,
        net_qos_routes,
        net_dpi_routes,
        net_content_filters_routes,
        net_acl_routes,
        net_oon_routes,
        net_port_forwards_routes,
        net_vouchers_routes,
        net_snmp_routes,
        # Cluster 6: stats / events / system. The network events router owns
        # the bare /events path for both products via a capability-aware
        # dispatcher; it must be included before protect_events_routes so the
        # network/protect-aware handler wins the path match.
        net_stats_routes,
        net_events_routes,
        net_system_routes,
    ):
        app.include_router(r.router, prefix="/v1")
    for r in (
        protect_cameras_routes,
        protect_events_routes,
        protect_recordings_routes,
        protect_lights_routes,
        protect_sensors_routes,
        protect_chimes_routes,
        protect_liveviews_routes,
        protect_system_routes,
    ):
        app.include_router(r.router, prefix="/v1")
    for r in (
        access_doors_routes,
        access_users_routes,
        access_credentials_routes,
        access_policies_routes,
        access_schedules_routes,
        access_devices_routes,
        access_visitors_routes,
        access_events_routes,
        access_system_routes,
    ):
        app.include_router(r.router, prefix="/v1")
    for r in (
        net_streams_routes,
        protect_streams_routes,
        access_streams_routes,
        net_per_device_routes,
        protect_per_camera_routes,
        access_per_door_routes,
    ):
        app.include_router(r.router, prefix="/v1")

    return app
