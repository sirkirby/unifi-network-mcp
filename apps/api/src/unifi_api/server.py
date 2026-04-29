"""FastAPI app factory."""

from __future__ import annotations

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
from unifi_api.routes import controllers as controllers_routes
from unifi_api.routes import health
from unifi_api.services.capability_cache import CapabilityCache
from unifi_api.services.managers import ManagerFactory
from unifi_api.services.manifest import ManifestRegistry


def create_app(config: ApiConfig) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup — manifest registry is loaded eagerly in create_app so it's
        # available even when the lifespan isn't run (e.g. ASGITransport tests).
        # Loading is idempotent and fast (file reads), so re-loading here keeps
        # the lifespan as the canonical startup hook.
        app.state.manifest_registry = ManifestRegistry.load_from_apps()
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
    app.state.argon_cache = ArgonVerifyCache()
    app.state.capability_cache = CapabilityCache()
    app.state.manifest_registry = ManifestRegistry.load_from_apps()

    app.include_router(health.router, prefix="/v1")
    app.include_router(controllers_routes.router, prefix="/v1")
    app.include_router(actions_routes.router, prefix="/v1")

    return app
