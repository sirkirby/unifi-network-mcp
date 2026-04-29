"""FastAPI app factory."""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request, Response
from starlette.middleware.cors import CORSMiddleware

from unifi_api.auth.cache import ArgonVerifyCache
from unifi_api.config import ApiConfig
from unifi_api.db.engine import create_engine
from unifi_api.db.session import get_sessionmaker
from unifi_api.routes import health


def create_app(config: ApiConfig) -> FastAPI:
    app = FastAPI(title="unifi-api", version="0.1.0", openapi_url="/v1/openapi.json", docs_url="/v1/docs")

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
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    # Wire DB
    # Validate the encryption key exists at startup; service refuses to start without it.
    ApiConfig.read_db_key()
    engine = create_engine(config.db.path)
    app.state.engine = engine
    app.state.sessionmaker = get_sessionmaker(engine)
    app.state.argon_cache = ArgonVerifyCache()

    @app.on_event("shutdown")
    async def _dispose_engine() -> None:
        await app.state.engine.dispose()

    app.include_router(health.router, prefix="/v1")

    return app
