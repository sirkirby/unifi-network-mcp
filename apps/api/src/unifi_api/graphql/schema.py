"""Strawberry schema for unifi-api. Code-first; SDL exported to schema.graphql.

PR1 ships only the smoke `health` field. PR2/3/4 add product-namespaced
NetworkQuery / ProtectQuery / AccessQuery roots.
"""

from __future__ import annotations

import sys

import strawberry

from unifi_api._version import __version__ as _api_version
from unifi_api.graphql.permissions import IsRead


@strawberry.type(description="Service health snapshot — smoke field for the GraphQL endpoint.")
class HealthSnapshot:
    ok: bool
    version: str
    python_version: str


@strawberry.type
class Query:
    @strawberry.field(
        permission_classes=[IsRead],
        description="Liveness probe; mirrors GET /v1/health/ready.",
    )
    def health(self) -> HealthSnapshot:
        return HealthSnapshot(
            ok=True,
            version=_api_version,
            python_version=sys.version.split()[0],
        )


schema = strawberry.Schema(query=Query)
