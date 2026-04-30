"""Helpers for the resource-route surface — used by /v1/catalog/resources
and the test_resource_route_coverage CI gate (Task 22)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from fastapi import FastAPI


@dataclass
class ResourceRoute:
    method: str
    path: str
    name: str  # function name


def collect_resource_routes(app: FastAPI) -> list[ResourceRoute]:
    """Walk the FastAPI app and return all GET routes under /v1/sites/."""
    routes: list[ResourceRoute] = []
    for r in app.routes:
        if not hasattr(r, "methods") or "GET" not in r.methods:
            continue
        if not r.path.startswith("/v1/sites/"):
            continue
        routes.append(ResourceRoute(method="GET", path=r.path, name=r.name))
    return routes


def is_read_tool(name: str) -> bool:
    """True if the tool name follows the read-tool convention (list_/get_/recent_)."""
    parts = name.split("_", 1)
    if len(parts) != 2:
        return False
    rest = parts[1]
    return rest.startswith(("list_", "get_", "recent_"))


def read_tools_in_manifest(all_tools: Iterable[str]) -> set[str]:
    return {t for t in all_tools if is_read_tool(t)}
